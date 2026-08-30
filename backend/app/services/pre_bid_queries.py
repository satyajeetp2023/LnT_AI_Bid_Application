from datetime import date,datetime,timezone
from fastapi import HTTPException
from sqlalchemy import case,func,or_,select
from sqlalchemy.orm import Session
from app.models import AuditEvent,BidDocument,BidMissingInput,BidPreBidQuery,BidRequirement
from app.services.pre_bid_query_taxonomy import CLOSED_STATUSES,OPEN_STATUSES

def validate_links(db:Session,project_id:int,requirement_id:int|None,missing_input_id:int|None,document_id:int|None):
 if requirement_id is not None:
  requirement=db.get(BidRequirement,requirement_id)
  if not requirement or requirement.bid_project_id!=project_id:raise HTTPException(422,"Requirement must belong to this bid project")
 if missing_input_id is not None:
  missing_input=db.get(BidMissingInput,missing_input_id)
  if not missing_input or missing_input.bid_project_id!=project_id:raise HTTPException(422,"Missing input must belong to this bid project")
 if document_id is not None:
  document=db.get(BidDocument,document_id)
  if not document or document.bid_project_id!=project_id:raise HTTPException(422,"Source document must belong to this bid project")

def normalize_workflow(item:BidPreBidQuery):
 if item.status=="Submitted" and item.submitted_date is None:item.submitted_date=date.today()
 if item.status=="Responded":
  if not (item.employer_response or "").strip():raise HTTPException(422,"Employer response is required when status is Responded")
  if item.response_date is None:item.response_date=date.today()

def _next_query_number(db:Session,project_id:int)->str:
 numbers=db.scalars(select(BidPreBidQuery.query_number).where(BidPreBidQuery.bid_project_id==project_id,BidPreBidQuery.query_number.is_not(None))).all()
 highest=0
 for value in numbers:
  if not value:continue
  digits="".join(ch for ch in value.split("-")[-1] if ch.isdigit())
  if digits:
   try:highest=max(highest,int(digits))
   except ValueError:pass
 return f"PBQ-{highest+1:03d}"

def create_pre_bid_query(db:Session,project_id:int,payload,user_id:int,request_metadata:dict):
 if payload.status=="Approved":raise HTTPException(422,"Use the approval workflow to approve a pre-bid query")
 validate_links(db,project_id,payload.requirement_id,payload.missing_input_id,payload.source_document_id)
 values=payload.model_dump();values["query_number"]=(values.get("query_number") or "").strip() or _next_query_number(db,project_id)
 item=BidPreBidQuery(**values,bid_project_id=project_id,created_by=user_id);normalize_workflow(item)
 if item.status in CLOSED_STATUSES:item.closed_by=user_id;item.closed_at=datetime.now(timezone.utc)
 db.add(item);db.flush();db.add(AuditEvent(user_id=user_id,bid_project_id=project_id,event_type="pre_bid_query.created",entity_type="BidPreBidQuery",entity_id=str(item.id),request_metadata=request_metadata,details={"pre_bid_query_id":item.id}));db.commit();return item

def list_pre_bid_queries(db:Session,project_id:int,filters:dict,page:int,page_size:int):
 q=select(BidPreBidQuery).where(BidPreBidQuery.bid_project_id==project_id);search=filters.get("search")
 if search:q=q.where(or_(BidPreBidQuery.query_title.ilike(f"%{search}%"),BidPreBidQuery.query_text.ilike(f"%{search}%"),BidPreBidQuery.query_number.ilike(f"%{search}%"),BidPreBidQuery.response_reference.ilike(f"%{search}%")))
 mapping={"query_category":BidPreBidQuery.query_category,"priority":BidPreBidQuery.priority,"status":BidPreBidQuery.status,"responsible_function":BidPreBidQuery.responsible_function,"requirement_id":BidPreBidQuery.requirement_id,"missing_input_id":BidPreBidQuery.missing_input_id,"source_document_id":BidPreBidQuery.source_document_id}
 for key,column in mapping.items():
  if filters.get(key) is not None:q=q.where(column==filters[key])
 if filters.get("target_response_from") is not None:q=q.where(BidPreBidQuery.target_response_date>=filters["target_response_from"])
 if filters.get("target_response_to") is not None:q=q.where(BidPreBidQuery.target_response_date<=filters["target_response_to"])
 total=db.scalar(select(func.count()).select_from(q.subquery())) or 0;order=case((BidPreBidQuery.priority=="Critical",1),(BidPreBidQuery.priority=="High",2),(BidPreBidQuery.priority=="Medium",3),else_=4)
 rows=db.scalars(q.order_by(order,BidPreBidQuery.target_response_date.asc().nullslast(),BidPreBidQuery.created_at.desc()).offset((page-1)*page_size).limit(page_size)).all();return rows,total

def update_pre_bid_query(db:Session,item:BidPreBidQuery,payload,user_id:int,request_metadata:dict):
 values=payload.model_dump(exclude_unset=True)
 if values.get("status")=="Approved" and item.status!="Approved":raise HTTPException(422,"Use the approval workflow to approve a pre-bid query")
 validate_links(db,item.bid_project_id,values.get("requirement_id",item.requirement_id),values.get("missing_input_id",item.missing_input_id),values.get("source_document_id",item.source_document_id));previous=item.status
 approval_sensitive={"query_title","query_text","query_category","priority","responsible_function","responsible_person","requirement_id","missing_input_id","source_document_id","source_page","source_clause","source_section","source_excerpt","impact_if_unresolved"}
 materially_changed=bool(approval_sensitive&set(values))
 for field,value in values.items():setattr(item,field,value)
 if previous=="Approved" and materially_changed:
  item.status="Ready for Review";item.approved_by=None;item.approved_at=None
 elif previous=="Approved" and values.get("status") in {"Draft","Ready for Review","Withdrawn"}:
  item.approved_by=None;item.approved_at=None
 normalize_workflow(item)
 if "status" in values:
  if item.status in CLOSED_STATUSES:item.closed_by=user_id;item.closed_at=datetime.now(timezone.utc)
  else:item.closed_by=None;item.closed_at=None
 event="pre_bid_query.closed" if item.status in CLOSED_STATUSES and previous not in CLOSED_STATUSES else "pre_bid_query.updated"
 db.add(AuditEvent(user_id=user_id,bid_project_id=item.bid_project_id,event_type=event,entity_type="BidPreBidQuery",entity_id=str(item.id),request_metadata=request_metadata,details={"pre_bid_query_id":item.id,"changed_fields":list(values)}));db.commit();return item

def approve_pre_bid_query(db:Session,item:BidPreBidQuery,user_id:int,request_metadata:dict):
 if item.status!="Ready for Review":raise HTTPException(422,"Only queries Ready for Review can be approved")
 item.status="Approved";item.approved_by=user_id;item.approved_at=datetime.now(timezone.utc)
 db.add(AuditEvent(user_id=user_id,bid_project_id=item.bid_project_id,event_type="pre_bid_query.approved",entity_type="BidPreBidQuery",entity_id=str(item.id),request_metadata=request_metadata,details={"pre_bid_query_id":item.id}))
 db.commit();return item

def revoke_pre_bid_query_approval(db:Session,item:BidPreBidQuery,user_id:int,request_metadata:dict):
 if item.status!="Approved" or item.approved_at is None:raise HTTPException(422,"Only approved queries can have approval revoked")
 item.status="Ready for Review";item.approved_by=None;item.approved_at=None
 db.add(AuditEvent(user_id=user_id,bid_project_id=item.bid_project_id,event_type="pre_bid_query.approval_revoked",entity_type="BidPreBidQuery",entity_id=str(item.id),request_metadata=request_metadata,details={"pre_bid_query_id":item.id}))
 db.commit();return item

def pre_bid_query_summary(db:Session,project_id:int):
 base=BidPreBidQuery.bid_project_id==project_id;today=date.today()
 def count(condition):return db.scalar(select(func.count()).select_from(BidPreBidQuery).where(base,condition)) or 0
 return {"total":count(BidPreBidQuery.id>0),"draft":count(BidPreBidQuery.status=="Draft"),"submitted":count(BidPreBidQuery.status=="Submitted"),"responded":count(BidPreBidQuery.status=="Responded"),"open":count(BidPreBidQuery.status.in_(OPEN_STATUSES)),"overdue":count((BidPreBidQuery.target_response_date<today)&(BidPreBidQuery.status=="Submitted"))}
