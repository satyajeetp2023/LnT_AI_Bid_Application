import re
from collections import Counter,defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlanningResourceEntry


MILESTONE_TYPES={"TT_Mile","TT_FinMile","TT_StartMile","TT_FinishMile"}
COMPLETE_STATUSES={"TK_Complete","Complete","Completed"}


def _terms(value):
 stop={"the","and","for","with","work","works","activity","task","of","to","in","at","section"}
 return {x for x in re.findall(r"[a-z0-9]+",str(value or "").lower()) if len(x)>1 and x not in stop}


def _score(a,b):
 aa=_terms(a);bb=_terms(b)
 if not aa or not bb:return 0.0
 overlap=len(aa&bb)
 return round(.65*overlap/max(1,min(len(aa),len(bb)))+.35*overlap/max(1,len(aa|bb)),3)


def _date(value):
 if not value:return None
 if isinstance(value,datetime):return value.date()
 text=str(value).strip()
 for fmt in ("%Y-%m-%d","%Y-%m-%d %H:%M:%S","%d-%b-%y","%d-%b-%Y","%d/%m/%Y"):
  try:return datetime.strptime(text[:19],fmt).date()
  except ValueError:pass
 try:return datetime.fromisoformat(text.replace("Z","+00:00")).date()
 except ValueError:return None


def _task_dates(task):
 start=next((_date(task.get(k)) for k in ("act_start_date","early_start_date","target_start_date","late_start_date") if _date(task.get(k))),None)
 finish=next((_date(task.get(k)) for k in ("act_end_date","early_end_date","target_end_date","late_end_date") if _date(task.get(k))),None)
 return start,finish


def _entry_dict(x):
 return {
  "id":x.id,"source_document_id":x.source_document_id,"plan_type":x.plan_type,
  "resource_category":x.resource_category,"resource_name":x.resource_name,"role_or_trade":x.role_or_trade,
  "activity_reference":x.activity_reference,"work_front":x.work_front,
  "quantity":float(x.quantity) if x.quantity is not None else None,"unit":x.unit,
  "start_date":x.start_date.isoformat() if x.start_date else None,
  "finish_date":x.finish_date.isoformat() if x.finish_date else None,
  "productivity_rate":float(x.productivity_rate) if x.productivity_rate is not None else None,
  "productivity_unit":x.productivity_unit,
 }


def reconcile_planning_package(db:Session,bid_id:int,tables:dict[str,list[dict]],capabilities:dict|None=None):
 capabilities=capabilities or {}
 tasks=[x for x in tables.get("TASK",[]) if x.get("task_type") not in MILESTONE_TYPES and x.get("status_code") not in COMPLETE_STATUSES]
 assignments=tables.get("TASKRSRC",[])
 resource_map={x.get("rsrc_id"):x for x in tables.get("RSRC",[]) if x.get("rsrc_id")}
 task_assignments=defaultdict(list)
 for a in assignments:
  if a.get("task_id"):task_assignments[a["task_id"]].append(a)

 entries=db.scalars(select(PlanningResourceEntry).where(
  PlanningResourceEntry.bid_project_id==bid_id
 )).all()
 staff=[x for x in entries if x.resource_category=="Staff" or x.plan_type=="Staff Plan"]
 external_resources=[x for x in entries if x not in staff]

 eligible_ids={x.get("task_id") for x in tasks if x.get("task_id")}
 schedule_loaded_ids={x for x in eligible_ids if task_assignments.get(x)}
 schedule_coverage=len(schedule_loaded_ids)/max(1,len(eligible_ids))

 if schedule_coverage>=.90:
  source_mode="Schedule Primary"
 elif schedule_coverage>0 and external_resources:
  source_mode="Combined Schedule + Separate Plans"
 elif schedule_coverage>0:
  source_mode="Partially Schedule Loaded"
 elif external_resources:
  source_mode="Separate Resource Plans"
 else:
  source_mode="No Resource Basis Available"

 mapped_external=defaultdict(list)
 external_matches=[]
 for entry in external_resources:
  reference=" ".join(x for x in (entry.activity_reference,entry.work_front) if x)
  if not reference:
   external_matches.append({**_entry_dict(entry),"match_status":"Unlinked","matched_task_code":None,"match_score":0.0})
   continue
  ranked=sorted(((_score(reference,f"{task.get('task_code','')} {task.get('task_name','')}"),task) for task in tasks),key=lambda x:-x[0])
  best_score,best=(ranked[0] if ranked else (0.0,None))
  if best and best_score>=.34:
   mapped_external[best.get("task_id")].append(entry)
   external_matches.append({**_entry_dict(entry),"match_status":"Matched" if best_score>=.55 else "Possible Match","matched_task_code":best.get("task_code"),"matched_task_name":best.get("task_name"),"match_score":best_score})
  else:
   external_matches.append({**_entry_dict(entry),"match_status":"Unlinked","matched_task_code":None,"match_score":best_score})

 coverage=[]
 for task in tasks:
  task_id=task.get("task_id")
  schedule_count=len(task_assignments.get(task_id,[]))
  external=mapped_external.get(task_id,[])
  if schedule_count:
   status="Schedule Loaded"
  elif external:
   status="Separate Plan"
  else:
   status="Uncovered"
  start,finish=_task_dates(task)
  coverage.append({
   "task_id":task_id,"task_code":task.get("task_code"),"task_name":task.get("task_name"),
   "start_date":start.isoformat() if start else None,"finish_date":finish.isoformat() if finish else None,
   "coverage_status":status,"schedule_assignment_count":schedule_count,
   "separate_plan_entries":[_entry_dict(x) for x in external],
  })

 covered=sum(1 for x in coverage if x["coverage_status"]!="Uncovered")
 combined_pct=round(covered*100/max(1,len(coverage)),1)

 task_dates=[d for task in tasks for d in _task_dates(task) if d]
 project_start=min(task_dates).isoformat() if task_dates else None
 project_finish=max(task_dates).isoformat() if task_dates else None

 role_counts=Counter((x.role_or_trade or x.resource_name).strip() for x in staff if (x.role_or_trade or x.resource_name))
 staff_without_dates=[x for x in staff if not x.start_date and not x.finish_date]
 staff_timeline=[{
  **_entry_dict(x),
  "covers_schedule_start":bool(project_start and x.start_date and x.start_date.isoformat()<=project_start),
  "covers_schedule_finish":bool(project_finish and x.finish_date and x.finish_date.isoformat()>=project_finish),
 } for x in staff]

 issues=[]
 if not tasks:
  issues.append({"severity":"High","type":"Schedule","message":"No executable schedule activities are available for resource reconciliation."})
 elif combined_pct<60:
  issues.append({"severity":"High","type":"Resource Coverage","message":f"Only {combined_pct}% of scheduled activities have resource evidence from the schedule or separate plans."})
 elif combined_pct<90:
  issues.append({"severity":"Medium","type":"Resource Coverage","message":f"{combined_pct}% of scheduled activities have identifiable resource evidence; review uncovered work fronts."})

 if schedule_coverage<.90 and not external_resources:
  issues.append({"severity":"High","type":"Missing Resource Plan","message":"The schedule is not broadly resource-loaded and no separate Resource/Equipment Plan has been identified."})
 if not staff:
  issues.append({"severity":"High","type":"Missing Staff Plan","message":"No bidder Staff Plan has been identified for management/supervision deployment review."})
 elif staff_without_dates:
  issues.append({"severity":"Medium","type":"Staff Timing","message":f"{len(staff_without_dates)} staff-plan entries have no mobilization/demobilization dates."})

 unlinked=[x for x in external_matches if x["match_status"]=="Unlinked"]
 if unlinked:
  issues.append({"severity":"Medium","type":"Unlinked Resources","message":f"{len(unlinked)} separate-plan entries are not linked to a recognizable scheduled activity/work front."})

 return {
  "resource_strategy":{
   "mode":source_mode,
   "schedule_resource_coverage_percent":round(schedule_coverage*100,1),
   "combined_activity_resource_coverage_percent":combined_pct,
   "schedule_assignments":len(assignments),
   "separate_resource_entries":len(external_resources),
   "staff_entries":len(staff),
   "rule":"Use schedule assignments when present; supplement or replace them with bidder separate plans when the schedule is not fully resource-loaded.",
  },
  "activity_resource_coverage":coverage,
  "separate_plan_matching":external_matches,
  "staff_plan":{
   "entries":staff_timeline,
   "role_summary":[{"role":k,"entries":v} for k,v in role_counts.most_common()],
   "entries_without_dates":len(staff_without_dates),
   "project_start":project_start,"project_finish":project_finish,
   "note":"Staff timing is compared with the programme timeline. Role adequacy is not inferred without contractual requirements or confirmed company norms.",
  },
  "issues":issues,
  "summary":{
   "schedule_activities":len(coverage),"resource_covered_activities":covered,
   "uncovered_activities":sum(1 for x in coverage if x["coverage_status"]=="Uncovered"),
   "schedule_loaded_activities":sum(1 for x in coverage if x["coverage_status"]=="Schedule Loaded"),
   "separate_plan_covered_activities":sum(1 for x in coverage if x["coverage_status"]=="Separate Plan"),
   "unlinked_resource_entries":len(unlinked),
   "high_issues":sum(1 for x in issues if x["severity"]=="High"),
   "medium_issues":sum(1 for x in issues if x["severity"]=="Medium"),
  },
  "version":"integrated-planning-package-v1",
  "note":"This reconciles evidence supplied by the bidder. It does not invent crew sizes, equipment quantities, staff norms or productivity assumptions.",
 }
