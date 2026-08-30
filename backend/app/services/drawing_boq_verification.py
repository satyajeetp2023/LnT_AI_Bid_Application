import re
from datetime import datetime,timezone
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent,DrawingBoqFinding,DrawingQuantityObservation,ScheduleScopeItem


STOP={"the","and","for","with","from","work","works","supply","installation","install","providing","complete","including","item","of","to","in"}


def _norm(text:str)->str:
 return re.sub(r"\s+"," ",str(text or "").lower()).strip()


def _terms(text:str):
 return {x for x in re.findall(r"[a-z0-9]+",_norm(text)) if len(x)>1 and x not in STOP}


def _unit(value:str|None):
 text=_norm(value)
 mapping={
  "no":"nos","nos.":"nos","number":"nos","numbers":"nos","each":"nos",
  "m":"m","meter":"m","metre":"m","meters":"m","metres":"m",
  "km":"km","kilometer":"km","kilometre":"km",
  "sqm":"m2","sq m":"m2","m2":"m2","m²":"m2",
  "cum":"m3","cu m":"m3","m3":"m3","m³":"m3",
  "lot":"lot","set":"set","sets":"set",
 }
 return mapping.get(text,text)


def _boq_data(item:ScheduleScopeItem):
 text=str(item.source_excerpt or "")
 match=re.search(r"BOQ\s+([^:|]+):\s*(.*?)(?:\s*\|\s*Qty:\s*([0-9,]+(?:\.\d+)?)\s*([^|]*))?$",text,re.I)
 reference=item.source_reference
 description=item.activity_name
 quantity=None;unit=None
 if match:
  reference=(match.group(1) or reference or "").strip() or reference
  description=(match.group(2) or description).strip()
  if match.group(3):
   quantity=Decimal(match.group(3).replace(",",""))
   unit=(match.group(4) or "").strip() or None
 return {
  "scope_item":item,"reference":reference,"description":description,
  "quantity":quantity,"unit":unit,
 }


def _match_score(observation:DrawingQuantityObservation,boq:dict):
 a=_terms(f"{observation.item_name} {observation.item_category or ''}")
 b=_terms(boq["description"])
 if not a or not b:return 0.0
 overlap=len(a&b)/max(1,len(a|b))
 coverage=len(a&b)/max(1,min(len(a),len(b)))
 seq=SequenceMatcher(None,_norm(observation.item_name),_norm(boq["description"])).ratio()
 return round(min(1.0,.45*coverage+.30*overlap+.25*seq),3)


def record_drawing_observations(
 db:Session,bid_id:int,document_id:int,observations:list[dict],user_id:int,
 extraction_method:str="Vision Extraction",request_metadata:dict|None=None
):
 existing=db.scalars(select(DrawingQuantityObservation).where(
  DrawingQuantityObservation.bid_project_id==bid_id,
  DrawingQuantityObservation.source_document_id==document_id,
 )).all()
 signatures={
  (
   str(x.source_page or ""),_norm(x.drawing_reference),_norm(x.item_name),
   str(x.quantity.normalize()),_unit(x.unit),x.extraction_method,
  ) for x in existing
 }
 created=[];skipped_duplicates=0
 for raw in observations:
  name=str(raw.get("item_name") or "").strip()
  unit=str(raw.get("unit") or "").strip()
  try:quantity=Decimal(str(raw.get("quantity")))
  except Exception:raise ValueError("Every drawing observation requires a valid quantity") from None
  if not name or not unit or quantity<0:raise ValueError("item_name, unit and non-negative quantity are required")
  confidence=Decimal(str(raw.get("confidence") if raw.get("confidence") is not None else ".50"))
  if confidence<0 or confidence>1:raise ValueError("confidence must be between 0 and 1")
  signature=(
   str(raw.get("source_page") or "").strip(),_norm(raw.get("drawing_reference")),_norm(name),
   str(quantity.normalize()),_unit(unit),extraction_method,
  )
  if signature in signatures:
   skipped_duplicates+=1
   continue
  row=DrawingQuantityObservation(
   bid_project_id=bid_id,source_document_id=document_id,
   source_page=str(raw.get("source_page") or "").strip() or None,
   drawing_reference=str(raw.get("drawing_reference") or "").strip() or None,
   item_name=name,item_category=str(raw.get("item_category") or "").strip() or None,
   quantity=quantity,unit=unit,
   evidence_text=str(raw.get("evidence_text") or "").strip() or None,
   evidence_region=raw.get("evidence_region") if isinstance(raw.get("evidence_region"),dict) else None,
   extraction_method=extraction_method,extraction_confidence=confidence,
   review_status="Needs Review",created_by=user_id,
  )
  db.add(row);db.flush();created.append(row);signatures.add(signature)
 db.add(AuditEvent(
  user_id=user_id,bid_project_id=bid_id,event_type="drawing.quantity_observations_recorded",
  entity_type="BidDocument",entity_id=str(document_id),request_metadata=request_metadata or {},
  details={"created":len(created),"skipped_duplicates":skipped_duplicates,"extraction_method":extraction_method},
 ))
 db.commit()
 return {"created":len(created),"skipped_duplicates":skipped_duplicates,"observation_ids":[x.id for x in created]}


def verify_drawing_boq(db:Session,bid_id:int,user_id:int|None=None,request_metadata:dict|None=None):
 observations=db.scalars(select(DrawingQuantityObservation).where(
  DrawingQuantityObservation.bid_project_id==bid_id
 ).order_by(DrawingQuantityObservation.id)).all()
 boq_items=db.scalars(select(ScheduleScopeItem).where(
  ScheduleScopeItem.bid_project_id==bid_id,
  ScheduleScopeItem.source_type=="BOQ",
  ScheduleScopeItem.parent_id.is_(None),
 )).all()
 boq=[_boq_data(x) for x in boq_items]

 existing_findings={
  x.observation_id:x for x in db.scalars(select(DrawingBoqFinding).where(
   DrawingBoqFinding.bid_project_id==bid_id
  )).all()
 }
 created=[];updated=0
 for observation in observations:
  ranked=sorted((( _match_score(observation,item),item) for item in boq),key=lambda x:-x[0])
  best_score,best=(ranked[0] if ranked else (0.0,None))
  if not best or best_score<.35:
   status="No BOQ Match"
   boq_qty=boq_unit=variance=variance_pct=None
   boq_ref=boq_desc=None;scope_id=None
  else:
   scope_id=best["scope_item"].id
   boq_ref=best["reference"];boq_desc=best["description"]
   boq_qty=best["quantity"];boq_unit=best["unit"]
   if boq_qty is None:
    status="BOQ Quantity Unavailable";variance=variance_pct=None
   elif _unit(boq_unit)!=_unit(observation.unit):
    status="Unit Review";variance=variance_pct=None
   else:
    variance=observation.quantity-boq_qty
    variance_pct=(variance*Decimal("100")/boq_qty) if boq_qty!=0 else None
    status="Match" if abs(variance)<=Decimal("0.000001") else "Quantity Variance"
  finding=existing_findings.get(observation.id)
  if finding:
   finding.boq_scope_item_id=scope_id
   finding.match_confidence=Decimal(str(best_score))
   finding.boq_reference=boq_ref;finding.boq_description=boq_desc
   finding.boq_quantity=boq_qty;finding.boq_unit=boq_unit
   finding.drawing_quantity=observation.quantity;finding.drawing_unit=observation.unit
   finding.variance_quantity=variance;finding.variance_percent=variance_pct
   finding.finding_status=status
   if finding.review_status=="Informational" and status!="Match":
    finding.review_status="Open"
   elif finding.review_status=="Open" and status=="Match" and not finding.reviewer_disposition:
    finding.review_status="Informational"
   updated+=1
  else:
   finding=DrawingBoqFinding(
    bid_project_id=bid_id,observation_id=observation.id,boq_scope_item_id=scope_id,
    match_confidence=Decimal(str(best_score)),boq_reference=boq_ref,boq_description=boq_desc,
    boq_quantity=boq_qty,boq_unit=boq_unit,drawing_quantity=observation.quantity,drawing_unit=observation.unit,
    variance_quantity=variance,variance_percent=variance_pct,finding_status=status,
    responsible_function="Engineering",review_status="Informational" if status=="Match" else "Open",
   )
   db.add(finding);db.flush();created.append(finding)
 if user_id is not None:
  db.add(AuditEvent(
   user_id=user_id,bid_project_id=bid_id,event_type="drawing_boq.verification_completed",
   entity_type="BidProject",entity_id=str(bid_id),request_metadata=request_metadata or {},
   details={"observations":len(observations),"boq_items":len(boq),"created_findings":len(created),"updated_findings":updated},
  ))
 db.commit()
 return drawing_boq_summary(db,bid_id)


def drawing_boq_summary(db:Session,bid_id:int):
 observations={x.id:x for x in db.scalars(select(DrawingQuantityObservation).where(
  DrawingQuantityObservation.bid_project_id==bid_id
 )).all()}
 rows=db.scalars(select(DrawingBoqFinding).where(
  DrawingBoqFinding.bid_project_id==bid_id
 ).order_by(DrawingBoqFinding.id)).all()
 items=[]
 for row in rows:
  obs=observations.get(row.observation_id)
  items.append({
   "id":row.id,"observation_id":row.observation_id,
   "source_document_id":obs.source_document_id if obs else None,
   "source_page":obs.source_page if obs else None,
   "drawing_reference":obs.drawing_reference if obs else None,
   "drawing_item":obs.item_name if obs else None,
   "drawing_quantity":float(row.drawing_quantity),"drawing_unit":row.drawing_unit,
   "extraction_method":obs.extraction_method if obs else None,
   "extraction_confidence":float(obs.extraction_confidence) if obs else None,
   "boq_scope_item_id":row.boq_scope_item_id,"boq_reference":row.boq_reference,
   "boq_description":row.boq_description,
   "boq_quantity":float(row.boq_quantity) if row.boq_quantity is not None else None,
   "boq_unit":row.boq_unit,"match_confidence":float(row.match_confidence),
   "variance_quantity":float(row.variance_quantity) if row.variance_quantity is not None else None,
   "variance_percent":float(row.variance_percent) if row.variance_percent is not None else None,
   "finding_status":row.finding_status,"responsible_function":row.responsible_function,"responsible_person":row.responsible_person,
   "review_status":row.review_status,
   "reviewer_disposition":row.reviewer_disposition,"reviewer_comment":row.reviewer_comment,
  })
 return {
  "items":items,
  "summary":{
   "observations":len(observations),"findings":len(items),
   "matched":sum(1 for x in items if x["finding_status"]=="Match"),
   "quantity_variances":sum(1 for x in items if x["finding_status"]=="Quantity Variance"),
   "unit_reviews":sum(1 for x in items if x["finding_status"]=="Unit Review"),
   "unmatched":sum(1 for x in items if x["finding_status"]=="No BOQ Match"),
   "open_reviews":sum(1 for x in items if x["review_status"]=="Open"),
  },
  "version":"drawing-boq-verification-v1",
  "note":"Drawing quantities are sanity-check evidence only. A mismatch is a review trigger, not an automatic BOQ correction.",
 }


def review_drawing_boq_finding(db:Session,finding_id:int,disposition:str,comment:str|None,user_id:int):
 allowed={"Confirmed Variance","BOQ Correct","Drawing Correct","Different Scope","Unit Conversion Required","False Match","Escalate"}
 if disposition not in allowed:raise ValueError("Unsupported drawing/BOQ disposition")
 row=db.get(DrawingBoqFinding,finding_id)
 if not row:raise ValueError("Drawing/BOQ finding not found")
 reviewer_comment=(comment or "").strip() or None
 if disposition!="Escalate" and not reviewer_comment:
  raise ValueError("A reviewer comment is required to close a drawing/BOQ finding")
 row.reviewer_disposition=disposition
 row.reviewer_comment=reviewer_comment
 row.review_status="Open" if disposition=="Escalate" else "Closed"
 row.reviewed_by=user_id;row.reviewed_at=datetime.now(timezone.utc)
 db.commit();db.refresh(row)
 return {"id":row.id,"review_status":row.review_status,"reviewer_disposition":row.reviewer_disposition}
