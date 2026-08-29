from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,Integer,JSON,String,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.database.session import Base
from .models import BidDocument,now

class BidPreparedArtifact(Base):
 __tablename__="bid_prepared_artifacts"
 id:Mapped[int]=mapped_column(primary_key=True)
 bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
 template_document_id:Mapped[int]=mapped_column(ForeignKey("bid_documents.id",ondelete="CASCADE"),index=True)
 template_document:Mapped[BidDocument]=relationship()
 artifact_name:Mapped[str]=mapped_column(String(300))
 artifact_type:Mapped[str]=mapped_column(String(100),default="Employer Template")
 file_extension:Mapped[str]=mapped_column(String(12),default="xlsx")
 storage_path:Mapped[str]=mapped_column(String(500))
 checksum:Mapped[str]=mapped_column(String(64),index=True)
 file_size:Mapped[int]=mapped_column(Integer)
 version_no:Mapped[int]=mapped_column(Integer,default=1)
 status:Mapped[str]=mapped_column(String(40),default="Draft",index=True)
 generation_summary:Mapped[dict]=mapped_column(JSON,default=dict)
 notes:Mapped[str|None]=mapped_column(Text)
 created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
 ready_for_review_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 ready_for_review_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 approved_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 approved_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 @property
 def template_name(self):return self.template_document.document_title or self.template_document.original_filename if self.template_document else None
