from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean,DateTime,ForeignKey,JSON,Numeric,String,Text
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base
from .models import now


class ClauseRiskPattern(Base):
    __tablename__="clause_risk_patterns"

    id:Mapped[int]=mapped_column(primary_key=True)
    risk_code:Mapped[str]=mapped_column(String(80),unique=True,index=True)
    title:Mapped[str]=mapped_column(String(300))
    category:Mapped[str]=mapped_column(String(100),index=True)
    severity:Mapped[str]=mapped_column(String(20),index=True)
    pattern_terms:Mapped[list]=mapped_column(JSON,default=list)
    exclusion_terms:Mapped[list]=mapped_column(JSON,default=list)
    explanation:Mapped[str]=mapped_column(Text)
    reviewer_guidance:Mapped[str|None]=mapped_column(Text)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    source_type:Mapped[str]=mapped_column(String(50),default="Firm Library")
    created_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)


class BidClauseRiskFinding(Base):
    __tablename__="bid_clause_risk_findings"

    id:Mapped[int]=mapped_column(primary_key=True)
    bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
    source_document_id:Mapped[int]=mapped_column(ForeignKey("bid_documents.id",ondelete="CASCADE"),index=True)
    risk_pattern_id:Mapped[int|None]=mapped_column(ForeignKey("clause_risk_patterns.id",ondelete="SET NULL"),index=True)
    risk_code:Mapped[str]=mapped_column(String(80),index=True)
    risk_title:Mapped[str]=mapped_column(String(300))
    risk_category:Mapped[str]=mapped_column(String(100),index=True)
    severity:Mapped[str]=mapped_column(String(20),index=True)
    source_page:Mapped[str|None]=mapped_column(String(50))
    source_clause:Mapped[str|None]=mapped_column(String(100))
    source_section:Mapped[str|None]=mapped_column(String(300))
    source_excerpt:Mapped[str]=mapped_column(Text)
    confidence:Mapped[Decimal]=mapped_column(Numeric(5,4))
    detection_method:Mapped[str]=mapped_column(String(60),default="Firm Risk Pattern")
    responsible_function:Mapped[str]=mapped_column(String(100),default="Contracts",index=True)
    responsible_person:Mapped[str|None]=mapped_column(String(200))
    review_status:Mapped[str]=mapped_column(String(40),default="Open",index=True)
    reviewer_disposition:Mapped[str|None]=mapped_column(String(50),index=True)
    reviewer_comment:Mapped[str|None]=mapped_column(Text)
    reviewed_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
    reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
