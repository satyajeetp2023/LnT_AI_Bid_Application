from datetime import date
from decimal import Decimal

from pydantic import BaseModel,Field,model_validator


RESULT_STATUSES={"Pending","Won","Lost","No Bid","Cancelled","Result Awaited"}


class BidPriceInput(BaseModel):
 bidder_name:str=Field(min_length=2,max_length=200)
 rank:int=Field(ge=1,le=100)
 bid_value:Decimal=Field(ge=0)
 currency:str=Field(default="INR",min_length=3,max_length=3)
 is_ours:bool=False
 source_reference:str|None=Field(None,max_length=500)


class BidOutcomeUpsert(BaseModel):
 result_status:str="Pending"
 result_date:date|None=None
 our_rank:int|None=Field(None,ge=1,le=100)
 our_bid_value:Decimal|None=Field(None,ge=0)
 our_margin_percent:Decimal|None=Field(None,ge=-100,le=100)
 awarded_bidder:str|None=Field(None,max_length=200)
 win_reason:str|None=Field(None,max_length=5000)
 loss_reason:str|None=Field(None,max_length=5000)
 source_reference:str|None=Field(None,max_length=500)
 notes:str|None=Field(None,max_length=5000)
 prices:list[BidPriceInput]=Field(default_factory=list,max_length=100)

 @model_validator(mode="after")
 def validate_result(self):
  if self.result_status not in RESULT_STATUSES:raise ValueError("Unsupported result status")
  ranks=[x.rank for x in self.prices]
  bidders=[" ".join(x.bidder_name.split()).casefold() for x in self.prices]
  if len(ranks)!=len(set(ranks)):raise ValueError("Bidder price ranks must be unique")
  if len(bidders)!=len(set(bidders)):raise ValueError("Bidder names must be unique within one result")
  if sum(1 for x in self.prices if x.is_ours)>1:raise ValueError("Only one bidder price row can be marked as ours")
  return self
