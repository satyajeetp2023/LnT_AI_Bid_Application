from collections import Counter,defaultdict
from decimal import Decimal

from sqlalchemy import delete,select
from sqlalchemy.orm import Session

from app.models import AuditEvent,BidOutcome,BidPriceRecord,BidProject


def _f(value):
 return float(value) if value is not None else None


def _pct_gap(value,base):
 value=_f(value);base=_f(base)
 if value is None or not base:return None
 return round((value-base)*100/base,2)


def price_summary(prices:list[dict]):
 rows=sorted(prices,key=lambda x:x["rank"])
 by_rank={x["rank"]:x for x in rows}
 l1=by_rank.get(1)
 ours=next((x for x in rows if x.get("is_ours")),None)
 gap=None;gap_pct=None
 if l1 and ours:
  gap=_f(ours["bid_value"])-_f(l1["bid_value"])
  if _f(l1["bid_value"]):
   gap_pct=round(gap*100/_f(l1["bid_value"]),2)
 market_spread={
  "l2_to_l1_percent":_pct_gap(by_rank.get(2,{}).get("bid_value") if by_rank.get(2) else None,l1.get("bid_value") if l1 else None),
  "l3_to_l1_percent":_pct_gap(by_rank.get(3,{}).get("bid_value") if by_rank.get(3) else None,l1.get("bid_value") if l1 else None),
  "l4_to_l1_percent":_pct_gap(by_rank.get(4,{}).get("bid_value") if by_rank.get(4) else None,l1.get("bid_value") if l1 else None),
  "recorded_bidders":len(rows),
 }
 return {
  "l1_to_l4":[x for x in rows if x["rank"]<=4],
  "our_price":ours,
  "l1":l1,
  "our_gap_to_l1":round(gap,2) if gap is not None else None,
  "our_gap_to_l1_percent":gap_pct,
  "market_spread":market_spread,
 }


def consistency_warnings(result_status:str,our_rank:int|None,prices:list[dict]):
 warnings=[]
 ours=next((x for x in prices if x.get("is_ours")),None)
 if result_status=="Won" and our_rank not in (None,1):
  warnings.append("Result is marked Won but our recorded rank is not L1.")
 if ours and our_rank is not None and ours["rank"]!=our_rank:
  warnings.append("Our outcome rank differs from the bidder-price row marked as ours.")
 if result_status=="Won" and ours and ours["rank"]!=1:
  warnings.append("Result is marked Won but the bidder-price row marked as ours is not rank 1.")
 return warnings


def outcome_dict(outcome:BidOutcome|None,prices:list[BidPriceRecord]):
 price_rows=[{
  "id":x.id,"bidder_name":x.bidder_name,"rank":x.rank,"bid_value":_f(x.bid_value),
  "currency":x.currency,"is_ours":x.is_ours,"source_reference":x.source_reference,
 } for x in sorted(prices,key=lambda x:x.rank)]
 if not outcome:return {"outcome":None,"prices":price_rows,"price_summary":price_summary(price_rows),"warnings":[]}
 data={
  "id":outcome.id,"bid_project_id":outcome.bid_project_id,"result_status":outcome.result_status,
  "result_date":outcome.result_date.isoformat() if outcome.result_date else None,
  "our_rank":outcome.our_rank,"our_bid_value":_f(outcome.our_bid_value),
  "our_margin_percent":_f(outcome.our_margin_percent),"awarded_bidder":outcome.awarded_bidder,
  "win_reason":outcome.win_reason,"loss_reason":outcome.loss_reason,
  "source_reference":outcome.source_reference,"notes":outcome.notes,
  "updated_at":outcome.updated_at.isoformat() if outcome.updated_at else None,
 }
 return {
  "outcome":data,"prices":price_rows,"price_summary":price_summary(price_rows),
  "warnings":consistency_warnings(outcome.result_status,outcome.our_rank,price_rows),
 }


def get_bid_outcome(db:Session,bid_id:int):
 outcome=db.scalar(select(BidOutcome).where(BidOutcome.bid_project_id==bid_id))
 prices=db.scalars(select(BidPriceRecord).where(BidPriceRecord.bid_project_id==bid_id).order_by(BidPriceRecord.rank)).all()
 return outcome_dict(outcome,prices)


def _normalized_payload(payload):
 outcome=payload.model_dump(mode="json",exclude={"prices"})
 rows=[{
  "bidder_name":" ".join(x.bidder_name.split()),
  "rank":x.rank,
  "bid_value":str(x.bid_value.normalize()) if x.bid_value is not None else None,
  "currency":x.currency.upper(),
  "is_ours":x.is_ours,
  "source_reference":x.source_reference,
 } for x in payload.prices]
 rows.sort(key=lambda x:x["rank"])
 return outcome,rows


def _normalized_persisted(outcome:BidOutcome,prices:list[BidPriceRecord]):
 data={
  "result_status":outcome.result_status,
  "result_date":outcome.result_date.isoformat() if outcome.result_date else None,
  "our_rank":outcome.our_rank,
  "our_bid_value":str(outcome.our_bid_value.normalize()) if outcome.our_bid_value is not None else None,
  "our_margin_percent":str(outcome.our_margin_percent.normalize()) if outcome.our_margin_percent is not None else None,
  "awarded_bidder":outcome.awarded_bidder,
  "win_reason":outcome.win_reason,
  "loss_reason":outcome.loss_reason,
  "source_reference":outcome.source_reference,
  "notes":outcome.notes,
 }
 rows=[{
  "bidder_name":" ".join(x.bidder_name.split()),
  "rank":x.rank,
  "bid_value":str(x.bid_value.normalize()),
  "currency":x.currency.upper(),
  "is_ours":x.is_ours,
  "source_reference":x.source_reference,
 } for x in prices]
 rows.sort(key=lambda x:x["rank"])
 return data,rows


def upsert_bid_outcome(db:Session,bid:BidProject,payload,user_id:int,request_metadata:dict|None=None):
 try:
  outcome=db.scalar(select(BidOutcome).where(BidOutcome.bid_project_id==bid.id))
  existing_prices=db.scalars(select(BidPriceRecord).where(BidPriceRecord.bid_project_id==bid.id).order_by(BidPriceRecord.rank)).all()
  if outcome is not None and _normalized_payload(payload)==_normalized_persisted(outcome,existing_prices):
   return outcome_dict(outcome,existing_prices)
  values=payload.model_dump(exclude={"prices"})
  if outcome is None:
   outcome=BidOutcome(bid_project_id=bid.id,created_by=user_id,updated_by=user_id,**values)
   db.add(outcome)
  else:
   for key,value in values.items():setattr(outcome,key,value)
   outcome.updated_by=user_id
  db.execute(delete(BidPriceRecord).where(BidPriceRecord.bid_project_id==bid.id))
  db.flush()
  for row in payload.prices:
   db.add(BidPriceRecord(
    bid_project_id=bid.id,bidder_name=" ".join(row.bidder_name.split()),rank=row.rank,
    bid_value=row.bid_value,currency=row.currency.upper(),is_ours=row.is_ours,
    source_reference=row.source_reference,created_by=user_id,
   ))
  db.flush()
  db.add(AuditEvent(
   user_id=user_id,bid_project_id=bid.id,event_type="historical_bid.outcome_saved",
   entity_type="BidProject",entity_id=str(bid.id),request_metadata=request_metadata or {},
   details={"result_status":payload.result_status,"our_rank":payload.our_rank,"price_rows":len(payload.prices)},
  ))
  db.commit()
 except Exception:
  db.rollback()
  raise
 return get_bid_outcome(db,bid.id)


def historical_bid_intelligence(db:Session,bid_ids:list[int]):
 if not bid_ids:
  return {"summary":{"recorded":0,"won":0,"lost":0,"win_rate_percent":None},"by_project_type":[],"by_client":[],"competitors":[],"market_spread":{"samples":0,"average_l2_to_l1_percent":None,"average_l3_to_l1_percent":None,"average_l4_to_l1_percent":None},"data_quality":{"completed_results":0,"outcome_source_coverage_percent":None,"price_source_coverage_percent":None,"complete_l1_l4_coverage_percent":None,"results_with_our_bid_marked_percent":None},"version":"phase7-historical-bid-intelligence-v3","note":"Descriptive only. No predictive judgement is produced."}
 outcomes=db.scalars(select(BidOutcome).where(BidOutcome.bid_project_id.in_(bid_ids))).all()
 projects={x.id:x for x in db.scalars(select(BidProject).where(BidProject.id.in_(bid_ids))).all()}
 prices=db.scalars(select(BidPriceRecord).where(BidPriceRecord.bid_project_id.in_(bid_ids))).all()
 completed=[x for x in outcomes if x.result_status in {"Won","Lost"}]
 won=[x for x in completed if x.result_status=="Won"]
 gaps=[];margins=[];ranks=[];market_spreads=[]
 for outcome in completed:
  rows=[x for x in prices if x.bid_project_id==outcome.bid_project_id]
  summary=price_summary([{"bidder_name":x.bidder_name,"rank":x.rank,"bid_value":_f(x.bid_value),"currency":x.currency,"is_ours":x.is_ours} for x in rows])
  if summary["our_gap_to_l1_percent"] is not None:gaps.append(summary["our_gap_to_l1_percent"])
  if outcome.our_margin_percent is not None:margins.append(_f(outcome.our_margin_percent))
  if outcome.our_rank is not None:ranks.append(outcome.our_rank)
  if summary["market_spread"]["l2_to_l1_percent"] is not None:market_spreads.append(summary["market_spread"])
 def grouped(field):
  bucket=defaultdict(list)
  for outcome in completed:
   project=projects.get(outcome.bid_project_id)
   if project:bucket[getattr(project,field) or "Unspecified"].append(outcome)
  return [{"name":k,"bids":len(v),"won":sum(x.result_status=="Won" for x in v),"win_rate_percent":round(sum(x.result_status=="Won" for x in v)*100/len(v),1)} for k,v in sorted(bucket.items())]
 appearances=Counter();wins=Counter();rank_totals=Counter();display_names={};client_context=defaultdict(Counter);project_type_context=defaultdict(Counter);head_to_head=Counter();competitor_ahead=Counter();our_ahead=Counter()
 our_rank_by_bid={}
 for outcome in completed:
  ours=next((x for x in prices if x.bid_project_id==outcome.bid_project_id and x.is_ours),None)
  if ours:our_rank_by_bid[outcome.bid_project_id]=ours.rank
 for row in prices:
  if row.is_ours:continue
  clean=" ".join(row.bidder_name.split());key=clean.casefold();display_names.setdefault(key,clean)
  appearances[key]+=1;rank_totals[key]+=row.rank
  project=projects.get(row.bid_project_id)
  if project:
   client_context[key][project.client or "Unspecified"]+=1
   project_type_context[key][project.project_type or "Unspecified"]+=1
  ours_rank=our_rank_by_bid.get(row.bid_project_id)
  if ours_rank is not None:
   head_to_head[key]+=1
   if row.rank<ours_rank:competitor_ahead[key]+=1
   elif row.rank>ours_rank:our_ahead[key]+=1
  if row.rank==1:wins[key]+=1
 def spread_average(key):
  values=[x[key] for x in market_spreads if x[key] is not None]
  return round(sum(values)/len(values),2) if values else None
 outcome_source_count=sum(bool((x.source_reference or "").strip()) for x in completed)
 price_rows_completed=[x for x in prices if x.bid_project_id in {o.bid_project_id for o in completed}]
 price_source_count=sum(bool((x.source_reference or "").strip()) for x in price_rows_completed)
 complete_l1_l4=0;with_ours=0
 for outcome in completed:
  rows=[x for x in price_rows_completed if x.bid_project_id==outcome.bid_project_id]
  recorded_ranks={x.rank for x in rows}
  if {1,2,3,4}<=recorded_ranks:complete_l1_l4+=1
  if any(x.is_ours for x in rows):with_ours+=1
 return {
  "summary":{
   "recorded":len(outcomes),"completed":len(completed),"won":len(won),"lost":len(completed)-len(won),
   "win_rate_percent":round(len(won)*100/len(completed),1) if completed else None,
   "average_our_rank":round(sum(ranks)/len(ranks),2) if ranks else None,
   "average_gap_to_l1_percent":round(sum(gaps)/len(gaps),2) if gaps else None,
   "average_recorded_margin_percent":round(sum(margins)/len(margins),2) if margins else None,
  },
  "by_project_type":grouped("project_type"),"by_client":grouped("client"),
  "competitors":[{"name":display_names[name],"appearances":count,"l1_wins":wins[name],"l1_rate_percent":round(wins[name]*100/count,1),"average_rank":round(rank_totals[name]/count,2),"top_client":client_context[name].most_common(1)[0][0] if client_context[name] else None,"top_project_type":project_type_context[name].most_common(1)[0][0] if project_type_context[name] else None,"head_to_head":head_to_head[name],"competitor_ahead":competitor_ahead[name],"our_ahead":our_ahead[name]} for name,count in appearances.most_common(20)],
  "market_spread":{
   "samples":len(market_spreads),
   "average_l2_to_l1_percent":spread_average("l2_to_l1_percent"),
   "average_l3_to_l1_percent":spread_average("l3_to_l1_percent"),
   "average_l4_to_l1_percent":spread_average("l4_to_l1_percent"),
  },
  "data_quality":{
   "completed_results":len(completed),
   "outcome_source_coverage_percent":round(outcome_source_count*100/len(completed),1) if completed else None,
   "price_source_coverage_percent":round(price_source_count*100/len(price_rows_completed),1) if price_rows_completed else None,
   "complete_l1_l4_coverage_percent":round(complete_l1_l4*100/len(completed),1) if completed else None,
   "results_with_our_bid_marked_percent":round(with_ours*100/len(completed),1) if completed else None,
  },
  "version":"phase7-historical-bid-intelligence-v3",
  "note":"This is descriptive historical intelligence from recorded bid outcomes and ranked prices. Market spread and data-quality coverage are evidence-based only. It does not predict future results.",
 }
