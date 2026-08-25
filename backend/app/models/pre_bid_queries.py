from datetime import date,datetime
from sqlalchemy import Date,DateTime,ForeignKey,String,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.database.session import Base
from .models import BidDocument,BidMissingInput,BidRequirement,now

class BidPreBidQuery(Base):
 __tablename__="bid_pre_bid_queries"
 id:Mapped[int]=mapped_column(primary_key=True)
 bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
 requirement_id:Mapped[int|None]=mapped_column(ForeignKey("bid_requirements.id",ondelete="SET NULL"),index=True)
 requirement:Mapped[BidRequirement|None]=relationship()
 missing_input_id:Mapped[int|None]=mapped_column(ForeignKey("bid_missing_inputs.id",ondelete="SET NULL"),index=True)
 missing_input:Mapped[BidMissingInput|None]=relationship()
 source_document_id:Mapped[int|None]=mapped_column(ForeignKey("bid_documents.id",ondelete="SET NULL"),index=True)
 source_document:Mapped[BidDocument|None]=relationship()
 query_number:Mapped[str|None]=mapped_column(String(100))
 query_title:Mapped[str]=mapped_column(String(300))
 query_text:Mapped[str]=mapped_column(Text)
 query_category:Mapped[str]=mapped_column(String(100))
 responsible_function:Mapped[str|None]=mapped_column(String(100),index=True)
 responsible_person:Mapped[str|None]=mapped_column(String(200))
 priority:Mapped[str]=mapped_column(String(20),default="Medium",index=True)
 status:Mapped[str]=mapped_column(String(40),default="Draft",index=True)
 target_response_date:Mapped[date|None]=mapped_column(Date,index=True)
 submitted_date:Mapped[date|None]=mapped_column(Date)
 employer_response:Mapped[str|None]=mapped_column(Text)
 response_date:Mapped[date|None]=mapped_column(Date)
 response_reference:Mapped[str|None]=mapped_column(String(200))
 impact_if_unresolved:Mapped[str|None]=mapped_column(Text)
 source_page:Mapped[str|None]=mapped_column(String(50))
 source_clause:Mapped[str|None]=mapped_column(String(100))
 source_section:Mapped[str|None]=mapped_column(String(200))
 source_excerpt:Mapped[str|None]=mapped_column(Text)
 created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
 closed_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 closed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 @property
 def requirement_title(self):return self.requirement.requirement_title if self.requirement else None
 @property
 def missing_input_title(self):return self.missing_input.missing_input_title if self.missing_input else None
 @property
 def source_original_filename(self):return self.source_document.original_filename if self.source_document else None
 @property
 def source_document_title(self):return self.source_document.document_title if self.source_document else None
