from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
 BidClauseRiskFinding,BidMissingInput,BidProject,BidRequirement,
 ExecutionLearningFactor,PlanningPackageFinding,
)
from app.services.historical_bid_comparison import historical_comparison
from app.services.submission_readiness import submission_readiness


def _clamp(value):return max(0,min(100,round(value,1)))


def _dimension(name:str,weight:int,penalties:list[dict],passes:list[str]):
 deducted=sum(x["points"] for x in penalties)
 score=_clamp(100-deducted)
 return {"name":name,"weight":weight,"score":score,"weighted_score":round(score*weight/100,2),"penalties":penalties,"passes":passes}


def bid_decision_analytics(db:Session,current:BidProject,visible_bid_ids:list[int]):
 requirements=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==current.id)).all()
 missing=db.scalars(select(BidMissingInput).where(BidMissingInput.bid_project_id==current.id)).all()
 clause_risks=db.scalars(select(BidClauseRiskFinding).where(BidClauseRiskFinding.bid_project_id==current.id)).all()
 planning=db.scalars(select(PlanningPackageFinding).where(PlanningPackageFinding.bid_project_id==current.id)).all()

 critical_requirements=[x for x in requirements if x.priority=="Critical" and x.requirement_status!="Closed"]
 noncompliant=[x for x in requirements if x.compliance_status=="Non-Compliant"]
 unreviewed_mandatory=[x for x in requirements if x.is_mandatory and x.review_status in {"Not Reviewed","Needs Clarification"}]
 open_critical_missing=[x for x in missing if x.status!="Resolved" and x.priority=="Critical"]
 open_high_missing=[x for x in missing if x.status!="Resolved" and x.priority=="High"]
 critical_clause=[x for x in clause_risks if x.review_status!="Closed" and x.severity=="Critical"]
 high_clause=[x for x in clause_risks if x.review_status!="Closed" and x.severity=="High"]
 high_planning=[x for x in planning if x.status=="Open" and x.severity=="High"]
 medium_planning=[x for x in planning if x.status=="Open" and x.severity=="Medium"]

 compliance_pen=[]
 if critical_requirements:compliance_pen.append({"code":"CRITICAL_REQUIREMENTS","points":min(60,len(critical_requirements)*15),"message":f"{len(critical_requirements)} critical requirement(s) remain open."})
 if noncompliant:compliance_pen.append({"code":"NON_COMPLIANT_REQUIREMENTS","points":min(60,len(noncompliant)*20),"message":f"{len(noncompliant)} requirement(s) are marked Non-Compliant."})
 if unreviewed_mandatory:compliance_pen.append({"code":"MANDATORY_UNREVIEWED","points":min(30,len(unreviewed_mandatory)*5),"message":f"{len(unreviewed_mandatory)} mandatory requirement(s) still need review."})
 compliance=_dimension("Compliance Readiness",25,compliance_pen,["No unresolved critical compliance issue detected."] if not compliance_pen else [])

 info_pen=[]
 if open_critical_missing:info_pen.append({"code":"CRITICAL_MISSING_INPUTS","points":min(70,len(open_critical_missing)*20),"message":f"{len(open_critical_missing)} critical missing input(s) remain open."})
 if open_high_missing:info_pen.append({"code":"HIGH_MISSING_INPUTS","points":min(40,len(open_high_missing)*8),"message":f"{len(open_high_missing)} high-priority missing input(s) remain open."})
 information=_dimension("Information Readiness",20,info_pen,["No critical/high missing input is open."] if not info_pen else [])

 risk_pen=[]
 if critical_clause:risk_pen.append({"code":"CRITICAL_CONTRACT_RISK","points":min(80,len(critical_clause)*25),"message":f"{len(critical_clause)} critical contractual risk finding(s) remain unresolved."})
 if high_clause:risk_pen.append({"code":"HIGH_CONTRACT_RISK","points":min(40,len(high_clause)*10),"message":f"{len(high_clause)} high contractual risk finding(s) remain unresolved."})
 risk=_dimension("Contract Risk Closure",20,risk_pen,["No open Critical/High contractual risk finding."] if not risk_pen else [])

 planning_pen=[]
 if high_planning:planning_pen.append({"code":"HIGH_PLANNING_FINDINGS","points":min(70,len(high_planning)*18),"message":f"{len(high_planning)} high planning finding(s) remain open."})
 if medium_planning:planning_pen.append({"code":"MEDIUM_PLANNING_FINDINGS","points":min(30,len(medium_planning)*6),"message":f"{len(medium_planning)} medium planning finding(s) remain open."})
 planning_dimension=_dimension("Planning Maturity",20,planning_pen,["No open High/Medium integrated planning finding."] if not planning_pen else [])

 sourced_requirements=[x for x in requirements if x.source_document_id is not None]
 reviewed_requirements=[x for x in requirements if x.review_status not in {"Not Reviewed","Needs Clarification"}]
 evidence_pen=[]
 if requirements:
  source_pct=len(sourced_requirements)*100/len(requirements)
  review_pct=len(reviewed_requirements)*100/len(requirements)
  if source_pct<80:evidence_pen.append({"code":"LOW_SOURCE_COVERAGE","points":round((80-source_pct)*0.75,1),"message":f"Requirement source linkage is {round(source_pct,1)}%."})
  if review_pct<80:evidence_pen.append({"code":"LOW_REVIEW_COVERAGE","points":round((80-review_pct)*0.75,1),"message":f"Requirement review coverage is {round(review_pct,1)}%."})
 else:
  source_pct=0;review_pct=0
  evidence_pen.append({"code":"NO_REQUIREMENTS","points":70,"message":"No requirement register evidence is available yet."})
 evidence=_dimension("Evidence Quality",15,evidence_pen,["Requirement evidence and review coverage are at least 80%."] if not evidence_pen else [])

 dimensions=[compliance,information,risk,planning_dimension,evidence]
 readiness_score=round(sum(x["weighted_score"] for x in dimensions),1)

 hard_blockers=[]
 if noncompliant:hard_blockers.append(f"{len(noncompliant)} requirement(s) marked Non-Compliant.")
 if critical_clause:hard_blockers.append(f"{len(critical_clause)} unresolved Critical contractual risk(s).")
 if open_critical_missing:hard_blockers.append(f"{len(open_critical_missing)} Critical missing input(s).")
 if high_planning:hard_blockers.append(f"{len(high_planning)} High planning finding(s).")

 try:
  submission=submission_readiness(db,current.id)
 except Exception:
  submission={"ready":False,"grade":"Unavailable","blockers":[],"warnings":["Submission readiness could not be evaluated from current evidence."]}
 if submission.get("blockers"):
  hard_blockers.extend([f"Submission: {x}" for x in submission["blockers"][:10]])

 comparison=historical_comparison(db,current,visible_bid_ids,10)

 similar_ids=[x["bid_project_id"] for x in comparison.get("matches",[]) if x.get("similarity_score",0)>=50]
 lessons=[]
 if similar_ids:
  factors=db.scalars(select(ExecutionLearningFactor).where(
   ExecutionLearningFactor.bid_project_id.in_(similar_ids),
   ExecutionLearningFactor.review_status=="Reviewed",
  )).all()
  factors=sorted(factors,key=lambda x:x.updated_at,reverse=True)[:20]
  lessons=[{
   "bid_project_id":x.bid_project_id,"category":x.factor_category,"impact_area":x.impact_area,
   "direction":x.direction,"title":x.title,"lesson_for_future_bids":x.lesson_for_future_bids,
   "source_reference":x.source_reference,"quantified_impact":float(x.quantified_impact) if x.quantified_impact is not None else None,
   "impact_unit":x.impact_unit,
  } for x in factors]

 if hard_blockers:posture="Blocked"
 elif readiness_score<75:posture="Management Review Required"
 else:posture="Ready for Management Decision"

 confidence_reasons=[]
 if comparison.get("summary",{}).get("comparable_bids",0)<3:confidence_reasons.append("Fewer than 3 comparable completed historical bids are available.")
 if not lessons:confidence_reasons.append("No reviewed execution lessons from sufficiently similar historical bids are available.")
 if evidence["score"]<80:confidence_reasons.append("Current-bid evidence quality is below 80%.")

 return {
  "bid_project_id":current.id,
  "decision_posture":posture,
  "readiness_score":readiness_score,
  "dimensions":dimensions,
  "hard_blockers":hard_blockers,
  "submission_readiness":{"ready":submission.get("ready",False),"grade":submission.get("grade"),"blocker_count":len(submission.get("blockers",[])),"warning_count":len(submission.get("warnings",[]))},
  "historical_context":comparison,
  "reviewed_execution_lessons":lessons,
  "confidence":{"level":"Limited" if len(confidence_reasons)>=2 else "Moderate" if confidence_reasons else "Strong","reasons":confidence_reasons},
  "methodology":{
   "type":"Deterministic evidence-weighted readiness, not win probability",
   "weights":{"compliance":25,"information":20,"contract_risk":20,"planning":20,"evidence":15},
   "hard_blocker_rule":"Any unresolved Non-Compliant requirement, Critical contract risk, Critical missing input, High planning finding, or submission blocker prevents Ready for Management Decision posture.",
  },
  "version":"phase9-bid-decision-analytics-v1",
  "note":"This module organizes evidence for management decision-making. It does not autonomously decide whether L&T should bid and does not predict win probability.",
 }
