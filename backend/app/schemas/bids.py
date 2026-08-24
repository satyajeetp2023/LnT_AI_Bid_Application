from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT_TYPES={"EPC","Design & Build","Item Rate","Lump Sum","Supply & Installation","Turnkey","Consultancy","Other"}
PROJECT_TYPES={"Railway Electrification","OHE","PSI","SCADA","Signalling","Telecom","Track","Civil","Bridges","Stations","Depot","Integrated Railway Package","Other"}
class BidCreate(BaseModel):
    bid_id: str=Field(min_length=3,max_length=50,pattern=r"^[A-Za-z0-9][A-Za-z0-9/_-]*$"); tender_reference_no: str=Field(min_length=2,max_length=100); client: str=Field(min_length=2,max_length=200); tender_name: str=Field(min_length=3,max_length=300); contract_type: str; project_type: str; package_section: str|None=None; location: str|None=None; estimated_value: Decimal|None=Field(None,ge=0); currency: str=Field(default="INR",min_length=3,max_length=3); tender_due_date: date; pre_bid_meeting_date: date|None=None; bid_manager: str=Field(min_length=2); co_bid_manager: str|None=None; current_stage: str="Opportunity"; bid_status: str="Draft"; description: str|None=Field(None,max_length=5000)
    @field_validator("contract_type")
    @classmethod
    def contract_valid(cls,v):
        if v not in CONTRACT_TYPES: raise ValueError("Unsupported contract type")
        return v
    @field_validator("project_type")
    @classmethod
    def project_valid(cls,v):
        if v not in PROJECT_TYPES: raise ValueError("Unsupported project type")
        return v
class BidRead(BidCreate):
    id:int; created_by:int; created_at:datetime; updated_at:datetime; model_config=ConfigDict(from_attributes=True)
class DocumentRead(BaseModel):
    id:int; bid_project_id:int; original_filename:str; file_extension:str; mime_type:str; file_size:int; checksum:str; document_status:str; document_category:str|None; information_tags:list; revision_no:str; is_latest_revision:bool; duplicate_of_document_id:int|None; uploaded_at:datetime; notes:str|None; model_config=ConfigDict(from_attributes=True)

