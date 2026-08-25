from datetime import date,datetime
from decimal import Decimal
from pydantic import BaseModel,ConfigDict,Field,field_validator
CONTRACT_TYPES={"EPC","Design & Build","Item Rate","Lump Sum","Supply & Installation","Turnkey","Consultancy","Other"}; PROJECT_TYPES={"Railway Electrification","OHE","PSI","SCADA","Signalling","Telecom","Track","Civil","Bridges","Stations","Depot","Integrated Railway Package","Other"}
class BidBase(BaseModel):
 bid_id:str=Field(min_length=3,max_length=50,pattern=r"^[A-Za-z0-9][A-Za-z0-9/_-]*$"); tender_reference_no:str=Field(min_length=2,max_length=100); client:str=Field(min_length=2,max_length=200); tender_name:str=Field(min_length=3,max_length=300); contract_type:str; project_type:str; package_section:str|None=None; location:str|None=None; estimated_value:Decimal|None=Field(None,ge=0); currency:str=Field(default="INR",min_length=3,max_length=3); tender_due_date:date; pre_bid_meeting_date:date|None=None; bid_manager:str=Field(min_length=2); co_bid_manager:str|None=None; current_stage:str="Opportunity"; bid_status:str="Draft"; description:str|None=Field(None,max_length=5000)
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
class BidCreate(BidBase): pass
class BidUpdate(BaseModel):
 tender_reference_no:str|None=None; client:str|None=None; tender_name:str|None=None; contract_type:str|None=None; project_type:str|None=None; package_section:str|None=None; location:str|None=None; estimated_value:Decimal|None=None; currency:str|None=None; tender_due_date:date|None=None; pre_bid_meeting_date:date|None=None; bid_manager:str|None=None; co_bid_manager:str|None=None; current_stage:str|None=None; bid_status:str|None=None; description:str|None=None
class BidRead(BidBase):
 id:int; created_by:int; created_at:datetime; updated_at:datetime; model_config=ConfigDict(from_attributes=True)
class DocumentRead(BaseModel):
 id:int; bid_project_id:int; original_filename:str; file_extension:str; mime_type:str; file_size:int; checksum:str; uploaded_by:int; uploader_name:str|None=None; document_status:str; document_category:str|None; document_type:str|None; document_number:str|None; document_title:str|None; revision:str|None; document_date:date|None; classification_status:str|None; classification_confidence:Decimal|None; is_latest_version:bool|None; remarks:str|None; document_subcategory:str|None; information_tags:list; revision_no:int; is_latest_revision:bool; revision_of_document_id:int|None; duplicate_of_document_id:int|None; uploaded_at:datetime; notes:str|None; model_config=ConfigDict(from_attributes=True)
class DocumentMetadataUpdate(BaseModel):
 document_category:str|None=None
 document_type:str|None=Field(None,max_length=100)
 document_number:str|None=Field(None,max_length=100)
 document_title:str|None=Field(None,max_length=300)
 revision:str|None=Field(None,max_length=50)
 document_date:date|None=None
 remarks:str|None=Field(None,max_length=5000)
class ClassificationUpdate(BaseModel):
 document_category:str; document_subcategory:str|None=None; information_tags:list[str]=Field(default_factory=list,max_length=25)
class NotesUpdate(BaseModel): notes:str|None=Field(None,max_length=5000)
class RevisionCreate(BaseModel): revision_of_document_id:int
