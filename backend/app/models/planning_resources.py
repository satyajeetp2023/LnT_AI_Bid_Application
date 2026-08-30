from datetime import date,datetime
from decimal import Decimal

from sqlalchemy import Date,DateTime,ForeignKey,Numeric,String,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base
from .models import now


class PlanningResourceEntry(Base):
    __tablename__="planning_resource_entries"
    __table_args__=(UniqueConstraint("source_document_id","source_sheet","source_row",name="uq_planning_resource_source_row"),)

    id:Mapped[int]=mapped_column(primary_key=True)
    bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
    source_document_id:Mapped[int]=mapped_column(ForeignKey("bid_documents.id",ondelete="CASCADE"),index=True)
    source_sheet:Mapped[str|None]=mapped_column(String(200))
    source_row:Mapped[int]=mapped_column()
    plan_type:Mapped[str]=mapped_column(String(40),index=True)  # Resource Plan / Equipment Plan / Staff Plan
    resource_category:Mapped[str]=mapped_column(String(40),index=True)  # Labour / Equipment / Staff / Other
    resource_name:Mapped[str]=mapped_column(String(250),index=True)
    role_or_trade:Mapped[str|None]=mapped_column(String(200),index=True)
    activity_reference:Mapped[str|None]=mapped_column(String(300),index=True)
    work_front:Mapped[str|None]=mapped_column(String(250),index=True)
    quantity:Mapped[Decimal|None]=mapped_column(Numeric(18,4))
    unit:Mapped[str|None]=mapped_column(String(40))
    start_date:Mapped[date|None]=mapped_column(Date,index=True)
    finish_date:Mapped[date|None]=mapped_column(Date,index=True)
    shift_hours:Mapped[Decimal|None]=mapped_column(Numeric(10,2))
    productivity_rate:Mapped[Decimal|None]=mapped_column(Numeric(18,6))
    productivity_unit:Mapped[str|None]=mapped_column(String(80))
    notes:Mapped[str|None]=mapped_column(Text)
    extraction_confidence:Mapped[Decimal]=mapped_column(Numeric(5,4))
    created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
