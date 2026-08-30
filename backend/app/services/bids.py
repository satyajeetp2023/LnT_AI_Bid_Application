from fastapi import HTTPException
from sqlalchemy import or_,select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import AuditEvent,BidProject,ProjectMembership
from app.schemas.bids import BidCreate,BidUpdate
from app.security.auth import is_admin

def create_bid(db:Session,data:BidCreate,user_id:int)->BidProject:
 bid=BidProject(**data.model_dump(),created_by=user_id); db.add(bid)
 try: db.flush()
 except IntegrityError: db.rollback(); raise HTTPException(409,"Bid ID already exists")
 db.add(ProjectMembership(bid_project_id=bid.id,user_id=user_id,role="Bid Manager")); db.add(AuditEvent(user_id=user_id,bid_project_id=bid.id,event_type="bid.created",entity_type="BidProject",entity_id=str(bid.id),details={"bid_id":bid.bid_id})); db.commit(); return bid
def list_bids(db:Session,user):
 query=select(BidProject).order_by(BidProject.updated_at.desc())
 if not is_admin(user): query=query.join(ProjectMembership).where(ProjectMembership.user_id==user.id)
 return db.scalars(query).unique().all()
def update_bid(db:Session,bid:BidProject,data:BidUpdate,user_id:int,metadata:dict)->BidProject:
 for key,value in data.model_dump(exclude_unset=True).items(): setattr(bid,key,value)
 db.add(AuditEvent(user_id=user_id,bid_project_id=bid.id,event_type="bid.edited",entity_type="BidProject",entity_id=str(bid.id),request_metadata=metadata,details={"fields":list(data.model_dump(exclude_unset=True))})); db.commit(); return bid
