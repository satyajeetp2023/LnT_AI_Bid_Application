from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidOutcome,BidPriceRecord,BidProject
from app.services.historical_bid_intelligence import price_summary


WEIGHTS={"project_type":35,"client":30,"contract_type":20,"location":15}


def _norm(value):
 return " ".join(str(value or "").strip().lower().split())


def similarity_score(current:BidProject,candidate:BidProject):
 matched=[];score=0
 for field,weight in WEIGHTS.items():
  left=_norm(getattr(current,field,None));right=_norm(getattr(candidate,field,None))
  if left and right and left==right:
   score+=weight;matched.append(field)
 return score,matched


def historical_comparison(db:Session,current:BidProject,visible_bid_ids:list[int],limit:int=10):
 candidate_ids=[x for x in visible_bid_ids if x!=current.id]
 if not candidate_ids:
  return {"current_bid_id":current.id,"matches":[],"summary":{"comparable_bids":0},"methodology":"Deterministic exact-field similarity using project type, client, contract type and location. Descriptive only.","version":"phase7-historical-comparison-v1"}

 outcomes=db.scalars(select(BidOutcome).where(BidOutcome.bid_project_id.in_(candidate_ids),BidOutcome.result_status.in_(["Won","Lost"]))).all()
 outcome_by_bid={x.bid_project_id:x for x in outcomes}
 if not outcome_by_bid:
  return {"current_bid_id":current.id,"matches":[],"summary":{"comparable_bids":0},"methodology":"Deterministic exact-field similarity using project type, client, contract type and location. Descriptive only.","version":"phase7-historical-comparison-v1"}

 projects=db.scalars(select(BidProject).where(BidProject.id.in_(list(outcome_by_bid)))).all()
 prices=db.scalars(select(BidPriceRecord).where(BidPriceRecord.bid_project_id.in_(list(outcome_by_bid)))).all()
 prices_by_bid={}
 for row in prices:prices_by_bid.setdefault(row.bid_project_id,[]).append(row)

 matches=[]
 for project in projects:
  score,fields=similarity_score(current,project)
  if score==0:continue
  outcome=outcome_by_bid[project.id]
  rows=[{"bidder_name":x.bidder_name,"rank":x.rank,"bid_value":float(x.bid_value),"currency":x.currency,"is_ours":x.is_ours} for x in prices_by_bid.get(project.id,[])]
  psummary=price_summary(rows)
  matches.append({
   "bid_project_id":project.id,"bid_id":project.bid_id,"tender_name":project.tender_name,
   "client":project.client,"project_type":project.project_type,"contract_type":project.contract_type,
   "location":project.location,"result_status":outcome.result_status,"our_rank":outcome.our_rank,
   "our_margin_percent":float(outcome.our_margin_percent) if outcome.our_margin_percent is not None else None,
   "our_gap_to_l1_percent":psummary["our_gap_to_l1_percent"],
   "similarity_score":score,"matched_fields":fields,
  })
 matches.sort(key=lambda x:(-x["similarity_score"],x["bid_id"]))
 matches=matches[:max(1,min(limit,50))]
 completed=len(matches);won=sum(x["result_status"]=="Won" for x in matches)
 gaps=[x["our_gap_to_l1_percent"] for x in matches if x["our_gap_to_l1_percent"] is not None]
 margins=[x["our_margin_percent"] for x in matches if x["our_margin_percent"] is not None]
 return {
  "current_bid_id":current.id,
  "summary":{
   "comparable_bids":completed,"won":won,"lost":completed-won,
   "win_rate_percent":round(won*100/completed,1) if completed else None,
   "average_gap_to_l1_percent":round(sum(gaps)/len(gaps),2) if gaps else None,
   "average_margin_percent":round(sum(margins)/len(margins),2) if margins else None,
  },
  "matches":matches,
  "methodology":"Deterministic exact-field similarity: project type 35, client 30, contract type 20, location 15. Only completed visible bids are compared. Descriptive only; no win prediction is produced.",
  "version":"phase7-historical-comparison-v1",
 }
