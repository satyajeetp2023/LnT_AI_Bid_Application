import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, JSON, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

class RoleName(str, enum.Enum):
    SYSTEM_ADMIN="System Admin"; BID_MANAGER="Bid Manager"; PROPOSAL_ENGINEER="Proposal Engineer"; PLANNING="Planning"; ENGINEERING="Engineering"; CONTRACTS="Contracts"; COMMERCIAL="Commercial"; PROCUREMENT="Procurement"; FINANCE="Finance"; MANAGEMENT_REVIEWER="Management Reviewer"; READ_ONLY="Read Only"

user_roles = Table("user_roles", Base.metadata, Column("user_id", ForeignKey("users.id"), primary_key=True), Column("role_id", ForeignKey("roles.id"), primary_key=True))

class Role(Base):
    __tablename__="roles"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[RoleName]=mapped_column(Enum(RoleName), unique=True)
class User(Base):
    __tablename__="users"; id: Mapped[int]=mapped_column(primary_key=True); email: Mapped[str]=mapped_column(String(255), unique=True); full_name: Mapped[str]=mapped_column(String(255)); is_active: Mapped[bool]=mapped_column(default=True); roles: Mapped[list[Role]]=relationship(secondary=user_roles)
class BidProject(Base):
    __tablename__="bid_projects"
    id: Mapped[int]=mapped_column(primary_key=True); bid_id: Mapped[str]=mapped_column(String(50), unique=True, index=True); tender_reference_no: Mapped[str]=mapped_column(String(100)); client: Mapped[str]=mapped_column(String(200)); tender_name: Mapped[str]=mapped_column(String(300)); contract_type: Mapped[str]=mapped_column(String(80)); project_type: Mapped[str]=mapped_column(String(100)); package_section: Mapped[str|None]=mapped_column(String(200)); location: Mapped[str|None]=mapped_column(String(200)); estimated_value: Mapped[Decimal|None]=mapped_column(Numeric(18,2)); currency: Mapped[str]=mapped_column(String(3), default="INR"); tender_due_date: Mapped[date]=mapped_column(Date); pre_bid_meeting_date: Mapped[date|None]=mapped_column(Date); bid_manager: Mapped[str]=mapped_column(String(200)); co_bid_manager: Mapped[str|None]=mapped_column(String(200)); current_stage: Mapped[str]=mapped_column(String(80), default="Opportunity"); bid_status: Mapped[str]=mapped_column(String(40), default="Draft"); description: Mapped[str|None]=mapped_column(Text); created_by: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone(), onupdate=lambda: datetime.now().astimezone())
class BidDocument(Base):
    __tablename__="bid_documents"
    id: Mapped[int]=mapped_column(primary_key=True); bid_project_id: Mapped[int]=mapped_column(ForeignKey("bid_projects.id"), index=True); original_filename: Mapped[str]=mapped_column(String(255)); stored_filename: Mapped[str|None]=mapped_column(String(255)); file_extension: Mapped[str]=mapped_column(String(12)); mime_type: Mapped[str]=mapped_column(String(150)); file_size: Mapped[int]=mapped_column(); checksum: Mapped[str]=mapped_column(String(64), index=True); storage_path: Mapped[str|None]=mapped_column(String(500)); uploaded_by: Mapped[int]=mapped_column(ForeignKey("users.id")); uploaded_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone()); document_status: Mapped[str]=mapped_column(String(40), default="Needs Review"); document_category: Mapped[str|None]=mapped_column(String(100)); document_subcategory: Mapped[str|None]=mapped_column(String(100)); information_tags: Mapped[list]=mapped_column(JSON, default=list); revision_no: Mapped[str]=mapped_column(String(20), default="1"); is_latest_revision: Mapped[bool]=mapped_column(Boolean, default=True); duplicate_of_document_id: Mapped[int|None]=mapped_column(ForeignKey("bid_documents.id")); source_type: Mapped[str]=mapped_column(String(50), default="Tender Upload"); notes: Mapped[str|None]=mapped_column(Text)
class ProjectMembership(Base):
    __tablename__="project_memberships"; id: Mapped[int]=mapped_column(primary_key=True); bid_project_id: Mapped[int]=mapped_column(ForeignKey("bid_projects.id")); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); role: Mapped[str]=mapped_column(String(50))
class AuditEvent(Base):
    __tablename__="audit_events"; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id")); event_type: Mapped[str]=mapped_column(String(80), index=True); entity_type: Mapped[str]=mapped_column(String(80)); entity_id: Mapped[str]=mapped_column(String(80)); timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone()); request_metadata: Mapped[dict]=mapped_column(JSON, default=dict); details: Mapped[dict]=mapped_column(JSON, default=dict)

