from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import AuditEvent, BidProject
from app.schemas.bids import BidCreate
def create_bid(db:Session,data:BidCreate,user_id:int)->BidProject:
    bid=BidProject(**data.model_dump(),created_by=user_id); db.add(bid)
    try: db.flush()
    except IntegrityError: db.rollback(); raise HTTPException(409,"Bid ID already exists")
    db.add(AuditEvent(user_id=user_id,event_type="bid.created",entity_type="BidProject",entity_id=str(bid.id),details={"bid_id":bid.bid_id})); db.commit(); return bid
def list_bids(db:Session): return db.scalars(select(BidProject).order_by(BidProject.updated_at.desc())).all()

