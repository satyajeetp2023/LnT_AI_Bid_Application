from datetime import datetime

from sqlalchemy import Boolean,DateTime,ForeignKey,Integer,String,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base
from .models import now


class TenderKnowledgeChunk(Base):
    __tablename__="tender_knowledge_chunks"
    __table_args__=(UniqueConstraint("source_document_id","chunk_index",name="uq_tender_chunk_document_index"),)

    id:Mapped[int]=mapped_column(primary_key=True)
    bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
    source_document_id:Mapped[int]=mapped_column(ForeignKey("bid_documents.id",ondelete="CASCADE"),index=True)
    chunk_index:Mapped[int]=mapped_column(Integer)
    source_page:Mapped[str|None]=mapped_column(String(50))
    source_clause:Mapped[str|None]=mapped_column(String(100))
    source_section:Mapped[str|None]=mapped_column(String(300))
    text:Mapped[str]=mapped_column(Text)
    text_hash:Mapped[str]=mapped_column(String(64),index=True)
    word_count:Mapped[int]=mapped_column(Integer,default=0)
    source_kind:Mapped[str]=mapped_column(String(60),default="Tender Document")
    is_active:Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
