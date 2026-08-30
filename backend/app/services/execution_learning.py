from datetime import datetime,timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent,BidOutcome,BidProject,ExecutionOutcome


def _f(value):return float(value) if value is not None else None


def _round(value):return round(value,2) if value is not None else None


def _won_outcome(db:Session,bid_id:int):
 outcome=db.scalar(select(BidOutcome).where(BidOutcome.bid_project_id==bid_id))
 if not outcome or outcome.result_status!="Won":
  raise HTTPException(409,"Execution learning is available only after the bid result is recorded as Won")
 return outcome


def execution_metrics(bid_outcome:BidOutcome,execution:ExecutionOutcome|None):
 if execution is None:
  return {
   "bid_value":_f(bid_outcome.our_bid_value),"bid_margin_percent":_f(bid_outcome.our_margin_percent),
   "revenue_change_vs_bid":None,"revenue_change_vs_bid_percent":None,"margin_change_percentage_points":None,
   "actual_duration_days":None,"cost_to_final_value_percent":None,"variation_share_percent":None,
   "claims_recovered_share_percent":None,
  }
 bid_value=_f(bid_outcome.our_bid_value);final_value=_f(execution.final_contract_value)
 revenue_change=None;revenue_pct=None
 if bid_value is not None and final_value is not None:
  revenue_change=final_value-bid_value
  if bid_value:revenue_pct=revenue_change*100/bid_value
 margin_delta=None
 if bid_outcome.our_margin_percent is not None and execution.final_margin_percent is not None:
  margin_delta=_f(execution.final_margin_percent)-_f(bid_outcome.our_margin_percent)
 duration=None
 if execution.actual_start_date and execution.actual_completion_date:
  duration=(execution.actual_completion_date-execution.actual_start_date).days
 cost_ratio=None
 if execution.actual_cost is not None and final_value:
  cost_ratio=_f(execution.actual_cost)*100/final_value
 variation_share=None
 if execution.approved_variations is not None and final_value:
  variation_share=_f(execution.approved_variations)*100/final_value
 claims_share=None
 if execution.claims_recovered is not None and final_value:
  claims_share=_f(execution.claims_recovered)*100/final_value
 return {
  "bid_value":bid_value,"bid_margin_percent":_f(bid_outcome.our_margin_percent),
  "revenue_change_vs_bid":_round(revenue_change),"revenue_change_vs_bid_percent":_round(revenue_pct),
  "margin_change_percentage_points":_round(margin_delta),"actual_duration_days":duration,
  "cost_to_final_value_percent":_round(cost_ratio),"variation_share_percent":_round(variation_share),
  "claims_recovered_share_percent":_round(claims_share),
 }


def _record(execution:ExecutionOutcome|None):
 if execution is None:return None
 return {
  "id":execution.id,"bid_project_id":execution.bid_project_id,"execution_status":execution.execution_status,
  "data_date":execution.data_date.isoformat() if execution.data_date else None,
  "actual_start_date":execution.actual_start_date.isoformat() if execution.actual_start_date else None,
  "actual_completion_date":execution.actual_completion_date.isoformat() if execution.actual_completion_date else None,
  "final_contract_value":_f(execution.final_contract_value),"actual_cost":_f(execution.actual_cost),
  "final_margin_percent":_f(execution.final_margin_percent),"approved_variations":_f(execution.approved_variations),
  "claims_recovered":_f(execution.claims_recovered),"eot_days":execution.eot_days,
  "source_reference":execution.source_reference,"notes":execution.notes,"review_status":execution.review_status,
  "reviewed_by":execution.reviewed_by,"reviewed_at":execution.reviewed_at.isoformat() if execution.reviewed_at else None,
  "updated_at":execution.updated_at.isoformat() if execution.updated_at else None,
 }


def get_execution_outcome(db:Session,bid_id:int):
 outcome=_won_outcome(db,bid_id)
 execution=db.scalar(select(ExecutionOutcome).where(ExecutionOutcome.bid_project_id==bid_id))
 return {
  "execution":_record(execution),
  "comparison":execution_metrics(outcome,execution),
  "learning_eligible":bool(execution and execution.review_status=="Reviewed"),
  "note":"Only reviewed execution actuals are included in portfolio learning. Missing values remain unknown and are never inferred.",
  "version":"phase8-execution-learning-v1",
 }


def save_execution_outcome(db:Session,bid:BidProject,payload,user_id:int,request_metadata:dict|None=None):
 _won_outcome(db,bid.id)
 execution=db.scalar(select(ExecutionOutcome).where(ExecutionOutcome.bid_project_id==bid.id))
 values=payload.model_dump()
 if execution is not None and all(getattr(execution,key)==value for key,value in values.items()):
  return get_execution_outcome(db,bid.id)
 try:
  if execution is None:
   execution=ExecutionOutcome(bid_project_id=bid.id,created_by=user_id,updated_by=user_id,**values)
   db.add(execution)
  else:
   for key,value in values.items():setattr(execution,key,value)
   execution.updated_by=user_id
   execution.review_status="Draft";execution.reviewed_by=None;execution.reviewed_at=None
  db.flush()
  db.add(AuditEvent(
   user_id=user_id,bid_project_id=bid.id,event_type="execution_learning.actuals_saved",
   entity_type="ExecutionOutcome",entity_id=str(execution.id),request_metadata=request_metadata or {},
   details={"execution_status":payload.execution_status,"source_reference":payload.source_reference},
  ))
  db.commit()
 except Exception:
  db.rollback();raise
 return get_execution_outcome(db,bid.id)


def review_execution_outcome(db:Session,bid:BidProject,user_id:int,request_metadata:dict|None=None):
 _won_outcome(db,bid.id)
 execution=db.scalar(select(ExecutionOutcome).where(ExecutionOutcome.bid_project_id==bid.id))
 if not execution:raise HTTPException(404,"Execution actuals have not been recorded")
 missing=[]
 if not (execution.source_reference or "").strip():missing.append("source reference")
 if not execution.data_date:missing.append("data date")
 if execution.execution_status in {"Completed","Closed"}:
  if not execution.actual_start_date:missing.append("actual start date")
  if not execution.actual_completion_date:missing.append("actual completion date")
 if all(value is None for value in (execution.final_contract_value,execution.actual_cost,execution.final_margin_percent,execution.approved_variations,execution.claims_recovered,execution.eot_days)):
  missing.append("at least one execution actual")
 if missing:raise HTTPException(409,"Execution actuals cannot be reviewed until these evidence fields are provided: "+", ".join(missing))
 execution.review_status="Reviewed";execution.reviewed_by=user_id;execution.reviewed_at=datetime.now(timezone.utc);execution.updated_by=user_id
 db.add(AuditEvent(
  user_id=user_id,bid_project_id=bid.id,event_type="execution_learning.actuals_reviewed",
  entity_type="ExecutionOutcome",entity_id=str(execution.id),request_metadata=request_metadata or {},
  details={"execution_status":execution.execution_status,"data_date":execution.data_date.isoformat() if execution.data_date else None},
 ))
 db.commit()
 return get_execution_outcome(db,bid.id)


def execution_learning_intelligence(db:Session,bid_ids:list[int]):
 if not bid_ids:
  return {"summary":{"reviewed_projects":0},"records":[],"version":"phase8-execution-learning-portfolio-v1","note":"Reviewed execution actuals only."}
 executions=db.scalars(select(ExecutionOutcome).where(ExecutionOutcome.bid_project_id.in_(bid_ids),ExecutionOutcome.review_status=="Reviewed")).all()
 if not executions:
  return {"summary":{"reviewed_projects":0},"records":[],"version":"phase8-execution-learning-portfolio-v1","note":"Reviewed execution actuals only."}
 outcomes={x.bid_project_id:x for x in db.scalars(select(BidOutcome).where(BidOutcome.bid_project_id.in_([e.bid_project_id for e in executions]))).all()}
 projects={x.id:x for x in db.scalars(select(BidProject).where(BidProject.id.in_([e.bid_project_id for e in executions]))).all()}
 records=[];revenue_changes=[];margin_changes=[];durations=[];eots=[]
 for execution in executions:
  outcome=outcomes.get(execution.bid_project_id)
  project=projects.get(execution.bid_project_id)
  if not outcome or outcome.result_status!="Won":continue
  metrics=execution_metrics(outcome,execution)
  if metrics["revenue_change_vs_bid_percent"] is not None:revenue_changes.append(metrics["revenue_change_vs_bid_percent"])
  if metrics["margin_change_percentage_points"] is not None:margin_changes.append(metrics["margin_change_percentage_points"])
  if metrics["actual_duration_days"] is not None:durations.append(metrics["actual_duration_days"])
  if execution.eot_days is not None:eots.append(execution.eot_days)
  records.append({
   "bid_project_id":execution.bid_project_id,"bid_id":project.bid_id if project else str(execution.bid_project_id),
   "tender_name":project.tender_name if project else None,"client":project.client if project else None,
   "project_type":project.project_type if project else None,"execution":_record(execution),"comparison":metrics,
  })
 return {
  "summary":{
   "reviewed_projects":len(records),
   "average_revenue_change_vs_bid_percent":_round(sum(revenue_changes)/len(revenue_changes)) if revenue_changes else None,
   "average_margin_change_percentage_points":_round(sum(margin_changes)/len(margin_changes)) if margin_changes else None,
   "average_actual_duration_days":_round(sum(durations)/len(durations)) if durations else None,
   "average_eot_days":_round(sum(eots)/len(eots)) if eots else None,
  },
  "records":records,
  "version":"phase8-execution-learning-portfolio-v1",
  "note":"Deterministic comparison of reviewed actuals against recorded winning bid values. No missing execution value is inferred.",
 }
