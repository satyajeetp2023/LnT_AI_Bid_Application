from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean,DateTime,ForeignKey,JSON,Numeric,String,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.database.session import Base
from .models import BidDocument,BidRequirement,now


class ScheduleScopeItem(Base):
 __tablename__="schedule_scope_items"
 id:Mapped[int]=mapped_column(primary_key=True)
 bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
 parent_id:Mapped[int|None]=mapped_column(ForeignKey("schedule_scope_items.id",ondelete="CASCADE"),index=True)
 source_requirement_id:Mapped[int|None]=mapped_column(ForeignKey("bid_requirements.id",ondelete="SET NULL"),index=True)
 source_requirement:Mapped[BidRequirement|None]=relationship()
 source_document_id:Mapped[int|None]=mapped_column(ForeignKey("bid_documents.id",ondelete="SET NULL"),index=True)
 source_document:Mapped[BidDocument|None]=relationship()
 activity_name:Mapped[str]=mapped_column(String(300))
 activity_level:Mapped[str]=mapped_column(String(40),default="Activity")
 source_type:Mapped[str]=mapped_column(String(60),index=True)
 source_reference:Mapped[str|None]=mapped_column(String(200))
 source_excerpt:Mapped[str|None]=mapped_column(Text)
 mandatory:Mapped[bool]=mapped_column(Boolean,default=True)
 responsible_function:Mapped[str]=mapped_column(String(100),default="Planning",index=True)
 responsible_person:Mapped[str|None]=mapped_column(String(200))
 match_keywords:Mapped[list]=mapped_column(JSON,default=list)
 coverage_status:Mapped[str]=mapped_column(String(40),default="Not Checked",index=True)
 matched_task_code:Mapped[str|None]=mapped_column(String(100))
 matched_task_name:Mapped[str|None]=mapped_column(String(500))
 match_confidence:Mapped[Decimal|None]=mapped_column(Numeric(5,4))
 disposition_status:Mapped[str]=mapped_column(String(40),default="Unexplained",index=True)
 disposition_reason:Mapped[str|None]=mapped_column(Text)
 disposition_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 disposition_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
