from datetime import date,datetime
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.services.pre_bid_query_taxonomy import QUERY_CATEGORIES,PRIORITIES,STATUSES,RESPONSIBLE_FUNCTIONS

class PreBidQueryFields(BaseModel):
 requirement_id:int|None=None;missing_input_id:int|None=None;source_document_id:int|None=None;query_number:str|None=Field(None,max_length=100);query_title:str=Field(min_length=2,max_length=300);query_text:str=Field(min_length=2,max_length=20000);query_category:str;responsible_function:str|None=None;responsible_person:str|None=Field(None,max_length=200);priority:str="Medium";status:str="Draft";target_response_date:date|None=None;submitted_date:date|None=None;employer_response:str|None=Field(None,max_length=20000);response_date:date|None=None;response_reference:str|None=Field(None,max_length=200);impact_if_unresolved:str|None=Field(None,max_length=10000);source_page:str|None=Field(None,max_length=50);source_clause:str|None=Field(None,max_length=100);source_section:str|None=Field(None,max_length=200);source_excerpt:str|None=Field(None,max_length=10000)
 @field_validator("query_category")
 @classmethod
 def category_valid(cls,v):
  if v not in QUERY_CATEGORIES:raise ValueError("Unsupported query category")
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

class PreBidQueryCreate(PreBidQueryFields):pass

class PreBidQueryUpdate(BaseModel):
 requirement_id:int|None=None;missing_input_id:int|None=None;source_document_id:int|None=None;query_number:str|None=None;query_title:str|None=Field(None,min_length=2,max_length=300);query_text:str|None=Field(None,min_length=2,max_length=20000);query_category:str|None=None;responsible_function:str|None=None;responsible_person:str|None=None;priority:str|None=None;status:str|None=None;target_response_date:date|None=None;submitted_date:date|None=None;employer_response:str|None=None;response_date:date|None=None;response_reference:str|None=None;impact_if_unresolved:str|None=None;source_page:str|None=None;source_clause:str|None=None;source_section:str|None=None;source_excerpt:str|None=None
 @field_validator("query_title","query_text","query_category","priority","status")
 @classmethod
 def required_fields_cannot_be_null(cls,v):
  if v is None:raise ValueError("Required pre-bid query fields cannot be null")
  return v
 @field_validator("query_category")
 @classmethod
 def category_valid(cls,v):
  if v is not None and v not in QUERY_CATEGORIES:raise ValueError("Unsupported query category")
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

class PreBidQueryRead(PreBidQueryFields):
 id:int;bid_project_id:int;created_by:int;created_at:datetime;updated_at:datetime;closed_by:int|None;closed_at:datetime|None;requirement_title:str|None=None;missing_input_title:str|None=None;source_original_filename:str|None=None;source_document_title:str|None=None;model_config=ConfigDict(from_attributes=True)


class PreBidQuerySuggestionDecision(BaseModel):
 source_kind:str=Field(min_length=2,max_length=80)
 source_id:int=Field(ge=1)
 decision:str="Do Not Raise"
 reason:str|None=Field(None,max_length=2000)
 @field_validator("decision")
 @classmethod
 def decision_valid(cls,v):
  if v not in {"Do Not Raise","Reconsider"}:raise ValueError("Unsupported suggestion decision")
  return v
