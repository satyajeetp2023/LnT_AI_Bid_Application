from datetime import date,datetime
from decimal import Decimal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.services.requirement_taxonomy import REQUIREMENT_CATEGORIES,REQUIREMENT_TYPES,PRIORITIES,REQUIREMENT_STATUSES,COMPLIANCE_STATUSES,REVIEW_STATUSES,RESPONSIBLE_FUNCTIONS
class RequirementFields(BaseModel):
 source_document_id:int|None=None; requirement_category:str; requirement_type:str|None=None; requirement_title:str=Field(min_length=2,max_length=300); requirement_text:str=Field(min_length=2,max_length=20000); source_page:str|None=Field(None,max_length=50); source_clause:str|None=Field(None,max_length=100); source_section:str|None=Field(None,max_length=200); source_excerpt:str|None=Field(None,max_length=10000); responsible_function:str|None=None; responsible_person:str|None=Field(None,max_length=200); due_date:date|None=None; priority:str="Medium"; requirement_status:str="Open"; is_mandatory:bool=False; compliance_status:str="Not Assessed"; review_status:str="Not Reviewed"; notes:str|None=Field(None,max_length=5000)
 @field_validator("requirement_category")
 @classmethod
 def category_valid(cls,v):
  if v not in REQUIREMENT_CATEGORIES: raise ValueError("Unsupported requirement category")
  return v
 @field_validator("requirement_type")
 @classmethod
 def type_valid(cls,v):
  if v is not None and v not in REQUIREMENT_TYPES: raise ValueError("Unsupported requirement type")
  return v
 @field_validator("priority")
 @classmethod
 def priority_valid(cls,v):
  if v not in PRIORITIES: raise ValueError("Unsupported priority")
  return v
 @field_validator("requirement_status")
 @classmethod
 def status_valid(cls,v):
  if v not in REQUIREMENT_STATUSES: raise ValueError("Unsupported requirement status")
  return v
 @field_validator("compliance_status")
 @classmethod
 def compliance_valid(cls,v):
  if v not in COMPLIANCE_STATUSES: raise ValueError("Unsupported compliance status")
  return v
 @field_validator("review_status")
 @classmethod
 def review_valid(cls,v):
  if v not in REVIEW_STATUSES: raise ValueError("Unsupported review status")
  return v
 @field_validator("responsible_function")
 @classmethod
 def function_valid(cls,v):
  if v is not None and v not in RESPONSIBLE_FUNCTIONS: raise ValueError("Unsupported responsible function")
  return v
class RequirementCreate(RequirementFields): pass
class RequirementUpdate(BaseModel):
 source_document_id:int|None=None; requirement_category:str|None=None; requirement_type:str|None=None; requirement_title:str|None=Field(None,min_length=2,max_length=300); requirement_text:str|None=Field(None,min_length=2,max_length=20000); source_page:str|None=None; source_clause:str|None=None; source_section:str|None=None; source_excerpt:str|None=None; responsible_function:str|None=None; responsible_person:str|None=None; due_date:date|None=None; priority:str|None=None; requirement_status:str|None=None; is_mandatory:bool|None=None; compliance_status:str|None=None; review_status:str|None=None; notes:str|None=None
 @field_validator("requirement_category","requirement_title","requirement_text","priority","requirement_status","is_mandatory","compliance_status","review_status")
 @classmethod
 def required_fields_cannot_be_null(cls,v):
  if v is None: raise ValueError("Required requirement fields cannot be null")
  return v
 @field_validator("requirement_category")
 @classmethod
 def category_valid(cls,v):
  if v is not None and v not in REQUIREMENT_CATEGORIES: raise ValueError("Unsupported requirement category")
  return v
 @field_validator("requirement_type")
 @classmethod
 def type_valid(cls,v):
  if v is not None and v not in REQUIREMENT_TYPES: raise ValueError("Unsupported requirement type")
  return v
 @field_validator("priority")
 @classmethod
 def priority_valid(cls,v):
  if v is not None and v not in PRIORITIES: raise ValueError("Unsupported priority")
  return v
 @field_validator("requirement_status")
 @classmethod
 def status_valid(cls,v):
  if v is not None and v not in REQUIREMENT_STATUSES: raise ValueError("Unsupported requirement status")
  return v
 @field_validator("compliance_status")
 @classmethod
 def compliance_valid(cls,v):
  if v is not None and v not in COMPLIANCE_STATUSES: raise ValueError("Unsupported compliance status")
  return v
 @field_validator("review_status")
 @classmethod
 def review_valid(cls,v):
  if v is not None and v not in REVIEW_STATUSES: raise ValueError("Unsupported review status")
  return v
 @field_validator("responsible_function")
 @classmethod
 def function_valid(cls,v):
  if v is not None and v not in RESPONSIBLE_FUNCTIONS: raise ValueError("Unsupported responsible function")
  return v
class RequirementRead(RequirementFields):
 id:int;bid_project_id:int;extraction_method:str;extraction_confidence:float|None;created_by:int;created_at:datetime;updated_at:datetime;reviewed_by:int|None;reviewed_at:datetime|None;source_original_filename:str|None=None;source_document_title:str|None=None;source_document_category:str|None=None;model_config=ConfigDict(from_attributes=True)
class RequirementExtractionSummary(BaseModel):
 document_id:int;created:int;skipped_duplicates:int;low_confidence_skipped:int;no_text:bool;extractor_version:str
