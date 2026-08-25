from datetime import date,datetime,timezone
from fastapi import HTTPException
from sqlalchemy import case,func,or_,select
from sqlalchemy.orm import Session
from app.models import AuditEvent,BidDocument,BidMissingInput,BidRequirement
from app.services.missing_input_taxonomy import OPEN_STATUSES,RESOLVED_STATUSES

def validate_links(db:Session,project_id:int,requirement_id:int|None,document_id:int|None):
 if requirement_id is not None:
  requirement=db.get(BidRequirement,requirement_id)
  if not requirement or requirement.bid_project_id!=project_id:raise HTTPException(422,"Requirement must belong to this bid project")
 if document_id is not None:
  document=db.get(BidDocument,document_id)
  if not document or document.bid_project_id!=project_id:raise HTTPException(422,"Source document must belong to this bid project")

def create_missing_input(db:Session,project_id:int,payload,user_id:int,request_metadata:dict):
 validate_links(db,project_id,payload.requirement_id,payload.source_document_id)
 item=BidMissingInput(**payload.model_dump(),bid_project_id=project_id,created_by=user_id)
 if item.status in RESOLVED_STATUSES:item.resolved_by=user_id;item.resolved_at=datetime.now(timezone.utc)
 db.add(item);db.flush();db.add(AuditEvent(user_id=user_id,bid_project_id=project_id,event_type="missing_input.created",entity_type="BidMissingInput",entity_id=str(item.id),request_metadata=request_metadata,details={"missing_input_id":item.id}));db.commit();return item

def list_missing_inputs(db:Session,project_id:int,filters:dict,page:int,page_size:int):
 q=select(BidMissingInput).where(BidMissingInput.bid_project_id==project_id);search=filters.get("search")
 if search:q=q.where(or_(BidMissingInput.missing_input_title.ilike(f"%{search}%"),BidMissingInput.missing_input_description.ilike(f"%{search}%"),BidMissingInput.requested_from.ilike(f"%{search}%")))
 mapping={"input_category":BidMissingInput.input_category,"input_type":BidMissingInput.input_type,"priority":BidMissingInput.priority,"status":BidMissingInput.status,"responsible_function":BidMissingInput.responsible_function,"requirement_id":BidMissingInput.requirement_id,"source_document_id":BidMissingInput.source_document_id}
 for key,column in mapping.items():
  if filters.get(key) is not None:q=q.where(column==filters[key])
 if filters.get("required_by_from") is not None:q=q.where(BidMissingInput.required_by_date>=filters["required_by_from"])
 if filters.get("required_by_to") is not None:q=q.where(BidMissingInput.required_by_date<=filters["required_by_to"])
 total=db.scalar(select(func.count()).select_from(q.subquery())) or 0;order=case((BidMissingInput.priority=="Critical",1),(BidMissingInput.priority=="High",2),(BidMissingInput.priority=="Medium",3),else_=4)
 rows=db.scalars(q.order_by(order,BidMissingInput.required_by_date.asc().nullslast(),BidMissingInput.created_at.desc()).offset((page-1)*page_size).limit(page_size)).all();return rows,total

def update_missing_input(db:Session,item:BidMissingInput,payload,user_id:int,request_metadata:dict):
 values=payload.model_dump(exclude_unset=True);validate_links(db,item.bid_project_id,values.get("requirement_id",item.requirement_id),values.get("source_document_id",item.source_document_id))
 previous_status=item.status
 for field,value in values.items():setattr(item,field,value)
 if "status" in values:
  if item.status in RESOLVED_STATUSES:item.resolved_by=user_id;item.resolved_at=datetime.now(timezone.utc)
  else:item.resolved_by=None;item.resolved_at=None
 event="missing_input.resolved" if item.status in RESOLVED_STATUSES and previous_status not in RESOLVED_STATUSES else "missing_input.updated"
 db.add(AuditEvent(user_id=user_id,bid_project_id=item.bid_project_id,event_type=event,entity_type="BidMissingInput",entity_id=str(item.id),request_metadata=request_metadata,details={"missing_input_id":item.id,"changed_fields":list(values)}));db.commit();return item

def missing_input_summary(db:Session,project_id:int):
 base=BidMissingInput.bid_project_id==project_id;today=date.today();count=lambda condition:db.scalar(select(func.count()).select_from(BidMissingInput).where(base,condition)) or 0
 return {"total":count(BidMissingInput.id>0),"critical":count(BidMissingInput.priority=="Critical"),"open":count(BidMissingInput.status.in_(OPEN_STATUSES)),"overdue":count(BidMissingInput.required_by_date<today,BidMissingInput.status.not_in(RESOLVED_STATUSES)) if False else count((BidMissingInput.required_by_date<today)&(BidMissingInput.status.not_in(RESOLVED_STATUSES))),"requested":count(BidMissingInput.status=="Requested"),"resolved":count(BidMissingInput.status=="Resolved")}
