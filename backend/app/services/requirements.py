from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import case,func,or_,select
from sqlalchemy.orm import Session
from app.models import AuditEvent,BidDocument,BidRequirement

def validate_source(db:Session,project_id:int,document_id:int|None):
 if document_id is None:return
 document=db.get(BidDocument,document_id)
 if not document or document.bid_project_id!=project_id:raise HTTPException(422,"Source document must belong to this bid project")
def create_requirement(db:Session,project_id:int,payload,user_id:int,request_metadata:dict):
 validate_source(db,project_id,payload.source_document_id);requirement=BidRequirement(**payload.model_dump(),bid_project_id=project_id,extraction_method="Manual",extraction_confidence=None,created_by=user_id);db.add(requirement);db.flush();db.add(AuditEvent(user_id=user_id,bid_project_id=project_id,event_type="requirement.created",entity_type="BidRequirement",entity_id=str(requirement.id),request_metadata=request_metadata,details={"requirement_id":requirement.id}));db.commit();return requirement
def list_requirements(db:Session,project_id:int,filters:dict,page:int,page_size:int):
 q=select(BidRequirement).where(BidRequirement.bid_project_id==project_id);search=filters.get("search")
 if search:q=q.where(or_(BidRequirement.requirement_title.ilike(f"%{search}%"),BidRequirement.requirement_text.ilike(f"%{search}%"),BidRequirement.source_clause.ilike(f"%{search}%"),BidRequirement.source_section.ilike(f"%{search}%")))
 mapping={"category":BidRequirement.requirement_category,"requirement_type":BidRequirement.requirement_type,"priority":BidRequirement.priority,"requirement_status":BidRequirement.requirement_status,"compliance_status":BidRequirement.compliance_status,"responsible_function":BidRequirement.responsible_function,"source_document_id":BidRequirement.source_document_id,"due_date":BidRequirement.due_date}
 for key,column in mapping.items():
  if filters.get(key) is not None:q=q.where(column==filters[key])
 total=db.scalar(select(func.count()).select_from(q.subquery())) or 0;order=case((BidRequirement.priority=="Critical",1),(BidRequirement.priority=="High",2),(BidRequirement.priority=="Medium",3),else_=4)
 rows=db.scalars(q.order_by(order,BidRequirement.due_date.asc().nullslast(),BidRequirement.created_at.desc()).offset((page-1)*page_size).limit(page_size)).all();return rows,total
def update_requirement(db:Session,requirement:BidRequirement,payload,user_id:int,request_metadata:dict):
 values=payload.model_dump(exclude_unset=True);validate_source(db,requirement.bid_project_id,values.get("source_document_id")) if "source_document_id" in values else None
 for field,value in values.items():setattr(requirement,field,value)
 if "review_status" in values:
  if values["review_status"]=="Reviewed":requirement.reviewed_by=user_id;requirement.reviewed_at=datetime.now(timezone.utc)
  else:requirement.reviewed_by=None;requirement.reviewed_at=None
 db.add(AuditEvent(user_id=user_id,bid_project_id=requirement.bid_project_id,event_type="requirement.updated",entity_type="BidRequirement",entity_id=str(requirement.id),request_metadata=request_metadata,details={"requirement_id":requirement.id,"changed_fields":list(values)}));db.commit();return requirement
