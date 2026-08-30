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


FACTOR_AREAS={"Cost","Time","Margin","Revenue","Productivity","Scope","Mixed"}
FACTOR_DIRECTIONS={"Adverse","Favorable","Neutral"}


class ExecutionLearningFactorInput(BaseModel):
 factor_category:str=Field(min_length=2,max_length=80)
 impact_area:str
 direction:str
 title:str=Field(min_length=3,max_length=300)
 description:str=Field(min_length=3,max_length=5000)
 quantified_impact:Decimal|None=Field(None,ge=0)
 impact_unit:str|None=Field(None,max_length=40)
 source_reference:str|None=Field(None,max_length=500)
 source_excerpt:str|None=Field(None,max_length=5000)
 lesson_for_future_bids:str|None=Field(None,max_length=5000)

 @model_validator(mode="after")
 def validate_factor(self):
  if self.impact_area not in FACTOR_AREAS:raise ValueError("Unsupported impact area")
  if self.direction not in FACTOR_DIRECTIONS:raise ValueError("Unsupported factor direction")
  return self
