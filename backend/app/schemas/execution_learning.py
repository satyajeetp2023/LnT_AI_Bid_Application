from datetime import date
from decimal import Decimal

from pydantic import BaseModel,Field,model_validator


EXECUTION_STATUSES={"Not Started","In Progress","Completed","Closed"}


class ExecutionOutcomeUpsert(BaseModel):
 execution_status:str="Not Started"
 data_date:date|None=None
 actual_start_date:date|None=None
 actual_completion_date:date|None=None
 final_contract_value:Decimal|None=Field(None,ge=0)
 actual_cost:Decimal|None=Field(None,ge=0)
 final_margin_percent:Decimal|None=Field(None,ge=-100,le=100)
 approved_variations:Decimal|None=Field(None,ge=0)
 claims_recovered:Decimal|None=Field(None,ge=0)
 eot_days:int|None=Field(None,ge=0)
 source_reference:str|None=Field(None,max_length=500)
 notes:str|None=Field(None,max_length=5000)

 @model_validator(mode="after")
 def validate_execution(self):
  if self.execution_status not in EXECUTION_STATUSES:raise ValueError("Unsupported execution status")
  if self.actual_start_date and self.actual_completion_date and self.actual_completion_date<self.actual_start_date:
   raise ValueError("Actual completion date cannot be before actual start date")
  return self
