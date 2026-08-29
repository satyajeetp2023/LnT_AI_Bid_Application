from collections import Counter
from datetime import date,timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidMissingInput,BidPreBidQuery,BidRequirement
from app.services.missing_input_taxonomy import RESOLVED_STATUSES
from app.services.responsibility_assignment import suggest_responsible_function


PRIORITY_ORDER={"Critical":0,"High":1,"Medium":2,"Low":3}


def _owner(category:str|None,text:str|None,current:str|None)->str:
    return current or suggest_responsible_function(category,text)


def department_work_queue(db:Session,bid_id:int,responsible_function:str|None=None,responsible_person:str|None=None):
    today=date.today()
    items=[]

    requirements=db.scalars(select(BidRequirement).where(
        BidRequirement.bid_project_id==bid_id,
        BidRequirement.requirement_status.notin_(["Closed","Not Applicable"]),
    )).all()
    for r in requirements:
        owner=_owner(r.requirement_category,r.requirement_text,r.responsible_function)
        if responsible_function and owner!=responsible_function:continue
        if responsible_person and r.responsible_person!=responsible_person:continue
        needs_action=r.review_status=="Not Reviewed" or r.compliance_status=="Not Assessed" or r.review_status=="Needs Clarification"
        if not needs_action:continue
        due=r.due_date.isoformat() if r.due_date else None
        overdue=bool(r.due_date and r.due_date<today)
        if r.review_status=="Not Reviewed":
            action="Review requirement"
            reason="Requirement has not been reviewed."
        elif r.review_status=="Needs Clarification":
            action="Resolve clarification"
            reason="Requirement is marked Needs Clarification."
        else:
            action="Assess compliance"
            reason="Compliance has not been assessed."
        items.append({
            "entity_type":"Requirement","entity_id":r.id,"title":r.requirement_title,
            "priority":r.priority,"responsible_function":owner,"responsible_person":r.responsible_person,
            "status":r.review_status if r.review_status!="Reviewed" else r.compliance_status,
            "due_date":due,"is_overdue":overdue,"action":action,"reason":reason,
            "route":f"/bids/{bid_id}/requirements","source_document":r.source_document_title or r.source_original_filename,
            "source_page":r.source_page,"source_clause":r.source_clause,
        })

    gaps=db.scalars(select(BidMissingInput).where(
        BidMissingInput.bid_project_id==bid_id,
        BidMissingInput.status.notin_(RESOLVED_STATUSES),
    )).all()
    for g in gaps:
        owner=_owner(g.input_category,f"{g.missing_input_title} {g.missing_input_description}",g.responsible_function)
        if responsible_function and owner!=responsible_function:continue
        if responsible_person and g.responsible_person!=responsible_person:continue
        due=g.required_by_date.isoformat() if g.required_by_date else None
        overdue=bool(g.required_by_date and g.required_by_date<today)
        items.append({
            "entity_type":"Missing Input","entity_id":g.id,"title":g.missing_input_title,
            "priority":g.priority,"responsible_function":owner,"responsible_person":g.responsible_person,
            "status":g.status,"due_date":due,"is_overdue":overdue,
            "action":"Close missing input","reason":"Required bid information or decision is still unresolved.",
            "route":f"/bids/{bid_id}/missing-inputs","source_document":g.source_document_title or g.source_original_filename,
            "source_page":g.source_page,"source_clause":g.source_clause,
        })

    queries=db.scalars(select(BidPreBidQuery).where(
        BidPreBidQuery.bid_project_id==bid_id,
        BidPreBidQuery.status.notin_(["Closed","Withdrawn","Responded"]),
    )).all()
    for q in queries:
        owner=_owner(q.query_category,q.query_text,q.responsible_function)
        if responsible_function and owner!=responsible_function:continue
        if responsible_person and q.responsible_person!=responsible_person:continue
        due=q.target_response_date.isoformat() if q.target_response_date else None
        overdue=bool(q.target_response_date and q.target_response_date<today and q.status=="Submitted")
        action="Review query" if q.status in {"Draft","Ready for Review"} else "Follow up Employer response" if q.status=="Submitted" else "Progress query"
        items.append({
            "entity_type":"Pre-Bid Query","entity_id":q.id,"title":q.query_title,
            "priority":q.priority,"responsible_function":owner,"responsible_person":q.responsible_person,
            "status":q.status,"due_date":due,"is_overdue":overdue,"action":action,
            "reason":"Pre-Bid Query still requires bidder or Employer action.",
            "route":f"/bids/{bid_id}/pre-bid-queries","source_document":q.source_document_title or q.source_original_filename,
            "source_page":q.source_page,"source_clause":q.source_clause,
        })

    due_soon_limit=today+timedelta(days=3)
    for item in items:
        due_obj=date.fromisoformat(item["due_date"]) if item["due_date"] else None
        item["days_to_due"]=(due_obj-today).days if due_obj else None
        item["is_due_soon"]=bool(due_obj and today<=due_obj<=due_soon_limit)
        if item["is_overdue"]:
            item["escalation_level"]="Red";item["escalation_reason"]="Action is overdue."
        elif item["priority"]=="Critical" and not item["responsible_person"]:
            item["escalation_level"]="Red";item["escalation_reason"]="Critical action has no named responsible person."
        elif item["is_due_soon"]:
            item["escalation_level"]="Amber";item["escalation_reason"]="Action is due within 3 days."
        elif item["priority"] in {"Critical","High"} and not item["responsible_person"]:
            item["escalation_level"]="Amber";item["escalation_reason"]="High-priority action has no named responsible person."
        else:
            item["escalation_level"]="None";item["escalation_reason"]=None

    items.sort(key=lambda x:(
        {"Red":0,"Amber":1,"None":2}.get(x["escalation_level"],3),
        0 if x["is_overdue"] else 1,
        PRIORITY_ORDER.get(x["priority"],4),
        x["due_date"] or "9999-12-31",
        x["entity_type"],x["title"].lower(),
    ))

    department_control=[]
    for function_name in sorted(set(x["responsible_function"] or "Unassigned" for x in items)):
        rows=[x for x in items if (x["responsible_function"] or "Unassigned")==function_name]
        department_control.append({
            "name":function_name,
            "open_actions":len(rows),
            "critical":sum(1 for x in rows if x["priority"]=="Critical"),
            "overdue":sum(1 for x in rows if x["is_overdue"]),
            "due_soon":sum(1 for x in rows if x["is_due_soon"]),
            "without_person":sum(1 for x in rows if not x["responsible_person"]),
            "red_escalations":sum(1 for x in rows if x["escalation_level"]=="Red"),
            "amber_escalations":sum(1 for x in rows if x["escalation_level"]=="Amber"),
        })
    department_control.sort(key=lambda x:(-x["red_escalations"],-x["amber_escalations"],-x["overdue"],-x["open_actions"],x["name"]))

    by_function=Counter(x["responsible_function"] or "Unassigned" for x in items)
    by_type=Counter(x["entity_type"] for x in items)
    return {
        "items":items,
        "summary":{
            "total":len(items),
            "critical":sum(1 for x in items if x["priority"]=="Critical"),
            "high":sum(1 for x in items if x["priority"]=="High"),
            "overdue":sum(1 for x in items if x["is_overdue"]),
            "unassigned":sum(1 for x in items if not x["responsible_function"]),
            "without_person":sum(1 for x in items if not x["responsible_person"]),
            "due_soon":sum(1 for x in items if x["is_due_soon"]),
            "red_escalations":sum(1 for x in items if x["escalation_level"]=="Red"),
            "amber_escalations":sum(1 for x in items if x["escalation_level"]=="Amber"),
        },
        "by_function":[{"name":k,"count":v} for k,v in by_function.most_common()],
        "by_type":[{"name":k,"count":v} for k,v in by_type.most_common()],
        "by_person":[{"name":k,"count":v} for k,v in Counter((x["responsible_person"] or "Unassigned") for x in items).most_common()],
        "department_control":department_control,
        "filter":{"responsible_function":responsible_function,"responsible_person":responsible_person},
        "version":"phase4-department-work-queue-v4",
    }
