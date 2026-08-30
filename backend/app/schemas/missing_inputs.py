from datetime import date,datetime
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.services.missing_input_taxonomy import INPUT_CATEGORIES,INPUT_TYPES,PRIORITIES,STATUSES,RESPONSIBLE_FUNCTIONS

class MissingInputFields(BaseModel):
 requirement_id:int|None=None;source_document_id:int|None=None;missing_input_title:str=Field(min_length=2,max_length=300);missing_input_description:str=Field(min_length=2,max_length=20000);input_category:str;input_type:str;responsible_function:str|None=None;responsible_person:str|None=Field(None,max_length=200);requested_from:str|None=Field(None,max_length=200);required_by_date:date|None=None;priority:str="Medium";status:str="Open";impact_if_missing:str|None=Field(None,max_length=10000);resolution_notes:str|None=Field(None,max_length=10000);source_page:str|None=Field(None,max_length=50);source_clause:str|None=Field(None,max_length=100);source_section:str|None=Field(None,max_length=200);source_excerpt:str|None=Field(None,max_length=10000)
 @field_validator("input_category")
 @classmethod
 def category_valid(cls,v):
  if v not in INPUT_CATEGORIES:raise ValueError("Unsupported input category")
  return v
 @field_validator("input_type")
 @classmethod
 def type_valid(cls,v):
  if v not in INPUT_TYPES:raise ValueError("Unsupported input type")
  return v
 @field_validator("priority")
 @classmethod
 def priority_valid(cls,v):
  if v not in PRIORITIES:raise ValueError("Unsupported priority")
  return v
 @field_validator("status")
 @classmethod
 def status_valid(cls,v):
  if v not in STATUSES:raise ValueError("Unsupported status")
  return v
 @field_validator("responsible_function")
 @classmethod
 def function_valid(cls,v):
  if v is not None and v not in RESPONSIBLE_FUNCTIONS:raise ValueError("Unsupported responsible function")
  return v
class MissingInputCreate(MissingInputFields):pass
class MissingInputUpdate(BaseModel):
 requirement_id:int|None=None;source_document_id:int|None=None;missing_input_title:str|None=Field(None,min_length=2,max_length=300);missing_input_description:str|None=Field(None,min_length=2,max_length=20000);input_category:str|None=None;input_type:str|None=None;responsible_function:str|None=None;responsible_person:str|None=None;requested_from:str|None=None;required_by_date:date|None=None;priority:str|None=None;status:str|None=None;impact_if_missing:str|None=None;resolution_notes:str|None=None;source_page:str|None=None;source_clause:str|None=None;source_section:str|None=None;source_excerpt:str|None=None
 @field_validator("missing_input_title","missing_input_description","input_category","input_type","priority","status")
 @classmethod
 def required_fields_cannot_be_null(cls,v):
  if v is None:raise ValueError("Required missing input fields cannot be null")
  return v
 @field_validator("input_category")
 @classmethod
 def category_valid(cls,v):
  if v is not None and v not in INPUT_CATEGORIES:raise ValueError("Unsupported input category")
  return v
 @field_validator("input_type")
 @classmethod
 def type_valid(cls,v):
  if v is not None and v not in INPUT_TYPES:raise ValueError("Unsupported input type")
  return v
 @field_validator("priority")
 @classmethod
 def priority_valid(cls,v):
  if v is not None and v not in PRIORITIES:raise ValueError("Unsupported priority")
  return v
 @field_validator("status")
 @classmethod
 def status_valid(cls,v):
  if v is not None and v not in STATUSES:raise ValueError("Unsupported status")
  return v
 @field_validator("responsible_function")
 @classmethod
 def function_valid(cls,v):
  if v is not None and v not in RESPONSIBLE_FUNCTIONS:raise ValueError("Unsupported responsible function")
  return v
class MissingInputRead(MissingInputFields):
 id:int;bid_project_id:int;created_by:int;created_at:datetime;updated_at:datetime;resolved_by:int|None;resolved_at:datetime|None;requirement_title:str|None=None;requirement_category:str|None=None;requirement_status:str|None=None;source_original_filename:str|None=None;source_document_title:str|None=None;model_config=ConfigDict(from_attributes=True)
