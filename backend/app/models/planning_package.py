from datetime import datetime

from sqlalchemy import DateTime,ForeignKey,String,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base
from .models import now


class PlanningPackageFinding(Base):
    __tablename__="planning_package_findings"
    __table_args__=(UniqueConstraint("bid_project_id","finding_key",name="uq_planning_package_finding_key"),)

    id:Mapped[int]=mapped_column(primary_key=True)
    bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
    schedule_document_id:Mapped[int|None]=mapped_column(ForeignKey("bid_documents.id",ondelete="SET NULL"),index=True)
    finding_key:Mapped[str]=mapped_column(String(300))
    finding_type:Mapped[str]=mapped_column(String(80),index=True)
    severity:Mapped[str]=mapped_column(String(20),index=True)
    title:Mapped[str]=mapped_column(String(300))
    description:Mapped[str]=mapped_column(Text)
    task_code:Mapped[str|None]=mapped_column(String(120),index=True)
    task_name:Mapped[str|None]=mapped_column(String(300))
    source_reference:Mapped[str|None]=mapped_column(String(300))
    responsible_function:Mapped[str]=mapped_column(String(100),default="Planning",index=True)
    responsible_person:Mapped[str|None]=mapped_column(String(200))
    status:Mapped[str]=mapped_column(String(40),default="Open",index=True)
    disposition:Mapped[str|None]=mapped_column(String(80))
    reviewer_comment:Mapped[str|None]=mapped_column(Text)
    reviewed_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
    reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
