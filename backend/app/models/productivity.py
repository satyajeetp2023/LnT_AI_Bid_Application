from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime,ForeignKey,Numeric,String,Text,Boolean
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base
from .models import now


class ProductivityBenchmark(Base):
    __tablename__="productivity_benchmarks"

    id:Mapped[int]=mapped_column(primary_key=True)
    activity_name:Mapped[str]=mapped_column(String(300),index=True)
    activity_key:Mapped[str]=mapped_column(String(300),index=True)
    project_type:Mapped[str|None]=mapped_column(String(200),index=True)
    discipline:Mapped[str|None]=mapped_column(String(100),index=True)
    unit:Mapped[str]=mapped_column(String(50),index=True)
    rate_per_working_day:Mapped[Decimal]=mapped_column(Numeric(18,6))
    resource_context:Mapped[str|None]=mapped_column(Text)
    source_type:Mapped[str]=mapped_column(String(50),default="User Confirmed",index=True)
    source_reference:Mapped[str|None]=mapped_column(String(300))
    bid_project_id:Mapped[int|None]=mapped_column(ForeignKey("bid_projects.id",ondelete="SET NULL"),index=True)
    confidence:Mapped[Decimal]=mapped_column(Numeric(5,4),default=Decimal("0.6000"))
    is_active:Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    notes:Mapped[str|None]=mapped_column(Text)
    created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
