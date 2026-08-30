from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime,ForeignKey,JSON,Numeric,String,Text
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base
from .models import now


class DrawingQuantityObservation(Base):
    __tablename__="drawing_quantity_observations"

    id:Mapped[int]=mapped_column(primary_key=True)
    bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
    source_document_id:Mapped[int]=mapped_column(ForeignKey("bid_documents.id",ondelete="CASCADE"),index=True)
    source_page:Mapped[str|None]=mapped_column(String(50))
    drawing_reference:Mapped[str|None]=mapped_column(String(200),index=True)
    item_name:Mapped[str]=mapped_column(String(300),index=True)
    item_category:Mapped[str|None]=mapped_column(String(100),index=True)
    quantity:Mapped[Decimal]=mapped_column(Numeric(18,6))
    unit:Mapped[str]=mapped_column(String(50),index=True)
    evidence_text:Mapped[str|None]=mapped_column(Text)
    evidence_region:Mapped[dict|None]=mapped_column(JSON)
    extraction_method:Mapped[str]=mapped_column(String(60),default="Vision Extraction")
    extraction_confidence:Mapped[Decimal]=mapped_column(Numeric(5,4))
    review_status:Mapped[str]=mapped_column(String(40),default="Needs Review",index=True)
    reviewer_comment:Mapped[str|None]=mapped_column(Text)
    reviewed_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
    reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)


class DrawingBoqFinding(Base):
    __tablename__="drawing_boq_findings"

    id:Mapped[int]=mapped_column(primary_key=True)
    bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
    observation_id:Mapped[int]=mapped_column(ForeignKey("drawing_quantity_observations.id",ondelete="CASCADE"),index=True)
    boq_scope_item_id:Mapped[int|None]=mapped_column(ForeignKey("schedule_scope_items.id",ondelete="SET NULL"),index=True)
    match_confidence:Mapped[Decimal]=mapped_column(Numeric(5,4))
    boq_reference:Mapped[str|None]=mapped_column(String(200))
    boq_description:Mapped[str|None]=mapped_column(String(500))
    boq_quantity:Mapped[Decimal|None]=mapped_column(Numeric(18,6))
    boq_unit:Mapped[str|None]=mapped_column(String(50))
    drawing_quantity:Mapped[Decimal]=mapped_column(Numeric(18,6))
    drawing_unit:Mapped[str]=mapped_column(String(50))
    variance_quantity:Mapped[Decimal|None]=mapped_column(Numeric(18,6))
    variance_percent:Mapped[Decimal|None]=mapped_column(Numeric(18,6))
    finding_status:Mapped[str]=mapped_column(String(50),index=True)
    responsible_function:Mapped[str]=mapped_column(String(100),default="Engineering",index=True)
    responsible_person:Mapped[str|None]=mapped_column(String(200))
    review_status:Mapped[str]=mapped_column(String(40),default="Open",index=True)
    reviewer_disposition:Mapped[str|None]=mapped_column(String(60))
    reviewer_comment:Mapped[str|None]=mapped_column(Text)
    reviewed_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
    reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
