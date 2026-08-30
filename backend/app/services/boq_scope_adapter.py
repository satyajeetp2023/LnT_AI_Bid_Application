import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent,ScheduleScopeItem


LIFECYCLE=(
    ("Design",("design","engineering","drawing","calculation")),
    ("Approval",("approval","approve","review")),
    ("Procurement / Supply",("procure","procurement","supply","manufacture","fabrication","delivery")),
    ("Installation / Erection",("install","installation","erect","erection","laying","construction","fixing")),
    ("Testing",("test","testing","inspection","fat","sat")),
    ("Commissioning",("commission","commissioning","energization","energisation")),
)
GENERIC_WORDS={"supply","providing","including","complete","all","with","and","for","the","work","works","item","lot","set","each","system","equipment"}


def _terms(text:str):
    return {x for x in re.findall(r"[a-z0-9]+",str(text or "").lower()) if len(x)>2 and x not in GENERIC_WORDS}


def _base_scope(description:str)->str:
    text=re.sub(r"\s+"," ",description).strip(" .;:-")
    if len(text)<=180:return text
    return text[:177]+"..."


def _phases(description:str):
    lower=description.lower()
    found=[]
    for phase,signals in LIFECYCLE:
        if any(signal in lower for signal in signals):
            found.append(phase)
    return found


def ingest_boq_scope(
    db:Session,
    bid_id:int,
    rows:list[dict],
    user_id:int,
    request_metadata:dict|None=None,
):
    existing=db.scalars(select(ScheduleScopeItem).where(
        ScheduleScopeItem.bid_project_id==bid_id,
        ScheduleScopeItem.source_type=="BOQ",
    )).all()
    by_ref={(x.source_reference or "",x.activity_name.lower()):x for x in existing}
    created=updated=skipped=0

    for index,row in enumerate(rows,1):
        reference=str(row.get("item_no") or row.get("reference") or index).strip()
        description=str(row.get("description") or row.get("item_description") or "").strip()
        if len(description)<3:
            skipped+=1;continue
        quantity=row.get("quantity")
        unit=row.get("unit")
        work_front=str(row.get("work_front") or "").strip() or None
        evidence=f"BOQ {reference}: {description}"
        if quantity not in (None,""):evidence+=f" | Qty: {quantity}"
        if unit not in (None,""):evidence+=f" {unit}"
        if work_front:evidence+=f" | Work Front: {work_front}"

        base=_base_scope(description)
        key=(reference,base.lower())
        parent=by_ref.get(key)
        if parent:
            parent.source_excerpt=evidence[:2000]
            parent.match_keywords=sorted(_terms(description))
            parent.mandatory=bool(row.get("mandatory",True))
            updated+=1
        else:
            parent=ScheduleScopeItem(
                bid_project_id=bid_id,
                activity_name=base,
                activity_level="BOQ Scope",
                source_type="BOQ",
                source_reference=reference,
                source_excerpt=evidence[:2000],
                mandatory=bool(row.get("mandatory",True)),
                match_keywords=sorted(_terms(description)),
                created_by=user_id,
            )
            db.add(parent);db.flush();created+=1
            by_ref[key]=parent

        phases=_phases(description)
        if len(phases)>1:
            for phase in phases:
                child_name=f"{phase}: {base}"
                child=db.scalar(select(ScheduleScopeItem).where(
                    ScheduleScopeItem.bid_project_id==bid_id,
                    ScheduleScopeItem.parent_id==parent.id,
                    ScheduleScopeItem.source_type=="BOQ",
                    ScheduleScopeItem.activity_name==child_name,
                ))
                if child:continue
                db.add(ScheduleScopeItem(
                    bid_project_id=bid_id,
                    parent_id=parent.id,
                    activity_name=child_name[:300],
                    activity_level="BOQ Sub-Activity",
                    source_type="BOQ",
                    source_reference=reference,
                    source_excerpt=evidence[:2000],
                    mandatory=bool(row.get("mandatory",True)),
                    match_keywords=sorted(_terms(f"{phase} {description}")),
                    created_by=user_id,
                ));created+=1

    db.add(AuditEvent(
        user_id=user_id,bid_project_id=bid_id,event_type="schedule.boq_scope_ingested",
        entity_type="BidProject",entity_id=str(bid_id),request_metadata=request_metadata or {},
        details={"rows_received":len(rows),"created":created,"updated":updated,"skipped":skipped},
    ))
    db.commit()
    return {"rows_received":len(rows),"created":created,"updated":updated,"skipped":skipped}
