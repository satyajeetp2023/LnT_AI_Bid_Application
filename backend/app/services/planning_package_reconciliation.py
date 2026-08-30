import re
from collections import Counter,defaultdict
from datetime import datetime,timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidRequirement,PlanningPackageFinding,PlanningResourceEntry


MILESTONE_TYPES={"TT_Mile","TT_FinMile","TT_StartMile","TT_FinishMile"}
COMPLETE_STATUSES={"TK_Complete","Complete","Completed"}
STAFF_ROLE_PATTERNS={
 "Project Manager":("project manager","project director"),
 "Planning Manager":("planning manager","planning engineer","scheduler"),
 "Construction Manager":("construction manager","site manager"),
 "Safety / HSE":("safety manager","safety officer","hse manager","hse officer"),
 "QA / QC":("qa/qc","qa qc","quality manager","quality engineer"),
 "Survey":("surveyor","survey manager","survey engineer"),
 "Design / Engineering":("design manager","design engineer","engineering manager"),
 "Testing & Commissioning":("testing and commissioning","t&c manager","commissioning manager","commissioning engineer"),
 "Contracts / Commercial":("contracts manager","commercial manager","quantity surveyor"),
}




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
   external_matches.append({**_entry_dict(entry),"match_status":"Unlinked","matched_task_code":None,"match_score":0.0,"timeline_status":"Not Checked","activity_start":None,"activity_finish":None})
   continue
  ranked=sorted(((_score(reference,f"{task.get('task_code','')} {task.get('task_name','')}"),task) for task in tasks),key=lambda x:-x[0])
  best_score,best=(ranked[0] if ranked else (0.0,None))
  if best and best_score>=.34:
   mapped_external[best.get("task_id")].append(entry)
   task_start,task_finish=_task_dates(best)
   if not entry.start_date and not entry.finish_date:
    timeline_status="Dates Not Provided"
   elif task_start and entry.start_date and entry.start_date>task_start:
    timeline_status="Starts After Activity"
   elif task_finish and entry.finish_date and entry.finish_date<task_finish:
    timeline_status="Ends Before Activity"
   else:
    timeline_status="Aligned / Overlapping"
   external_matches.append({**_entry_dict(entry),"match_status":"Matched" if best_score>=.55 else "Possible Match","matched_task_code":best.get("task_code"),"matched_task_name":best.get("task_name"),"match_score":best_score,"timeline_status":timeline_status,"activity_start":task_start.isoformat() if task_start else None,"activity_finish":task_finish.isoformat() if task_finish else None})
  else:
   external_matches.append({**_entry_dict(entry),"match_status":"Unlinked","matched_task_code":None,"match_score":best_score,"timeline_status":"Not Checked","activity_start":None,"activity_finish":None})

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

 requirements=db.scalars(select(BidRequirement).where(
  BidRequirement.bid_project_id==bid_id,
  BidRequirement.requirement_status.notin_(["Closed","Not Applicable"]),
 )).all()
 requirement_text="\n".join(f"{x.requirement_title} {x.requirement_text}" for x in requirements).lower()
 required_staff=[]
 staff_text=" ".join(f"{x.resource_name} {x.role_or_trade or ''}" for x in staff).lower()
 for role,signals in STAFF_ROLE_PATTERNS.items():
  matched_signals=[signal for signal in signals if signal in requirement_text]
  if not matched_signals:continue
  present=any(signal in staff_text for signal in signals)
  required_staff.append({
   "role":role,"present_in_staff_plan":present,
   "contract_signals":matched_signals,
  })

 temporal_misalignment=[x for x in external_matches if x.get("timeline_status") in {"Starts After Activity","Ends Before Activity"}]

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

 if temporal_misalignment:
  issues.append({"severity":"Medium","type":"Resource Timing","message":f"{len(temporal_misalignment)} separate-plan entries do not cover the full linked activity period."})

 missing_contract_staff=[x for x in required_staff if not x["present_in_staff_plan"]]
 if missing_contract_staff:
  issues.append({"severity":"High","type":"Contract Staff Requirement","message":"Contract-required staff roles are not identifiable in the Staff Plan: "+", ".join(x["role"] for x in missing_contract_staff)})

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
   "contract_required_roles":required_staff,
   "missing_contract_required_roles":[x["role"] for x in required_staff if not x["present_in_staff_plan"]],
   "note":"Staff timing is compared with the programme timeline. Staff-role checks are raised only where the tender evidence explicitly requires that role; otherwise no staffing norm is invented.",
  },
  "issues":issues,
  "summary":{
   "schedule_activities":len(coverage),"resource_covered_activities":covered,
   "uncovered_activities":sum(1 for x in coverage if x["coverage_status"]=="Uncovered"),
   "schedule_loaded_activities":sum(1 for x in coverage if x["coverage_status"]=="Schedule Loaded"),
   "separate_plan_covered_activities":sum(1 for x in coverage if x["coverage_status"]=="Separate Plan"),
   "unlinked_resource_entries":len(unlinked),
   "resource_timing_misalignments":len(temporal_misalignment),
   "contract_required_staff_roles":len(required_staff),
   "missing_contract_staff_roles":len(missing_contract_staff),
   "high_issues":sum(1 for x in issues if x["severity"]=="High"),
   "medium_issues":sum(1 for x in issues if x["severity"]=="Medium"),
  },
  "version":"integrated-planning-package-v2",
  "note":"This reconciles evidence supplied by the bidder. It does not invent crew sizes, equipment quantities, staff norms or productivity assumptions.",
 }


def _finding_candidates(analysis:dict):
 candidates=[]
 for issue in analysis.get("issues",[]):
  key="issue:"+re.sub(r"[^a-z0-9]+","-",issue["type"].lower()).strip("-")
  candidates.append({
   "finding_key":key,"finding_type":issue["type"],"severity":issue["severity"],
   "title":issue["type"],"description":issue["message"],
   "task_code":None,"task_name":None,"source_reference":None,
  })
 for row in analysis.get("activity_resource_coverage",[]):
  if row.get("coverage_status")!="Uncovered":continue
  task_key=str(row.get("task_code") or row.get("task_id") or row.get("task_name") or "unknown")
  candidates.append({
   "finding_key":"uncovered-activity:"+task_key,
   "finding_type":"Uncovered Activity","severity":"High",
   "title":"Scheduled activity has no identifiable resource coverage",
   "description":f"{task_key} - {row.get('task_name') or 'Unnamed activity'} is not resource-loaded in the schedule and has no matched separate resource/equipment-plan entry.",
   "task_code":row.get("task_code"),"task_name":row.get("task_name"),"source_reference":None,
  })
 for row in analysis.get("separate_plan_matching",[]):
  if row.get("timeline_status") in {"Starts After Activity","Ends Before Activity"}:
   candidates.append({
    "finding_key":f"resource-timing:{row['id']}",
    "finding_type":"Resource Timing","severity":"Medium",
    "title":"Resource deployment does not cover linked activity period",
    "description":f"{row.get('resource_name')} - {row.get('timeline_status')} for {row.get('matched_task_code') or row.get('matched_task_name') or 'linked activity'}.",
    "task_code":row.get("matched_task_code"),"task_name":row.get("matched_task_name"),
    "source_reference":row.get("activity_reference") or row.get("work_front"),
   })
  if row.get("match_status")=="Unlinked":
   candidates.append({
    "finding_key":f"unlinked-resource:{row['id']}",
    "finding_type":"Unlinked Resource","severity":"Medium",
    "title":"Separate-plan resource is not linked to a schedule activity",
    "description":f"{row.get('resource_name')} has no reliable link to a scheduled activity/work front.",
    "task_code":None,"task_name":None,"source_reference":row.get("activity_reference") or row.get("work_front"),
   })
 for role in analysis.get("staff_plan",{}).get("missing_contract_required_roles",[]):
  candidates.append({
   "finding_key":"contract-staff:"+re.sub(r"[^a-z0-9]+","-",role.lower()).strip("-"),
   "finding_type":"Contract Staff Requirement","severity":"High",
   "title":"Contract-required staff role missing from Staff Plan",
   "description":f"{role} is explicitly indicated by tender requirement evidence but is not identifiable in the bidder Staff Plan.",
   "task_code":None,"task_name":None,"source_reference":role,
  })
 # Dedupe by stable key, keeping highest severity.
 priority={"High":2,"Medium":1,"Low":0}
 dedup={}
 for candidate in candidates:
  previous=dedup.get(candidate["finding_key"])
  if previous is None or priority.get(candidate["severity"],0)>priority.get(previous["severity"],0):
   dedup[candidate["finding_key"]]=candidate
 return list(dedup.values())


def sync_planning_package_findings(
 db:Session,bid_id:int,schedule_document_id:int,analysis:dict
):
 candidates=_finding_candidates(analysis)
 current={x.finding_key:x for x in db.scalars(select(PlanningPackageFinding).where(
  PlanningPackageFinding.bid_project_id==bid_id
 )).all()}
 active_keys=set()
 created=updated=cleared=0
 for item in candidates:
  key=item["finding_key"];active_keys.add(key)
  row=current.get(key)
  if row:
   row.schedule_document_id=schedule_document_id
   row.finding_type=item["finding_type"];row.severity=item["severity"]
   row.title=item["title"];row.description=item["description"]
   row.task_code=item["task_code"];row.task_name=item["task_name"];row.source_reference=item["source_reference"]
   if row.status in {"Open","Cleared by Re-analysis"}:
    row.status="Open";row.disposition=None;row.reviewer_comment=None;row.reviewed_by=None;row.reviewed_at=None
   updated+=1
  else:
   db.add(PlanningPackageFinding(
    bid_project_id=bid_id,schedule_document_id=schedule_document_id,
    responsible_function="Planning",status="Open",**item
   ));created+=1
 for key,row in current.items():
  if key in active_keys:continue
  if row.status=="Open":
   row.status="Cleared by Re-analysis"
   row.disposition="No Longer Detected"
   row.reviewer_comment="The issue was not detected in the latest integrated planning-package analysis."
   row.reviewed_at=datetime.now(timezone.utc)
   cleared+=1
 db.commit()
 return {
  "created":created,"updated":updated,"cleared":cleared,
  "active_findings":len(candidates),
 }


def planning_package_findings(db:Session,bid_id:int):
 rows=db.scalars(select(PlanningPackageFinding).where(
  PlanningPackageFinding.bid_project_id==bid_id
 ).order_by(PlanningPackageFinding.status,PlanningPackageFinding.severity,PlanningPackageFinding.created_at)).all()
 return {
  "items":[{
   "id":x.id,"schedule_document_id":x.schedule_document_id,"finding_key":x.finding_key,
   "finding_type":x.finding_type,"severity":x.severity,"title":x.title,"description":x.description,
   "task_code":x.task_code,"task_name":x.task_name,"source_reference":x.source_reference,
   "responsible_function":x.responsible_function,"responsible_person":x.responsible_person,
   "status":x.status,"disposition":x.disposition,"reviewer_comment":x.reviewer_comment,
  } for x in rows],
  "summary":{
   "total":len(rows),"open":sum(1 for x in rows if x.status=="Open"),
   "high_open":sum(1 for x in rows if x.status=="Open" and x.severity=="High"),
   "medium_open":sum(1 for x in rows if x.status=="Open" and x.severity=="Medium"),
   "cleared":sum(1 for x in rows if x.status=="Cleared by Re-analysis"),
  },
  "version":"integrated-planning-package-findings-v1",
 }


def review_planning_package_finding(db:Session,finding_id:int,disposition:str,comment:str|None,user_id:int):
 allowed={"Resolved","Accepted / Explained","To Be Revised","Not Applicable","Escalate"}
 if disposition not in allowed:raise ValueError("Unsupported planning-package disposition")
 row=db.get(PlanningPackageFinding,finding_id)
 if not row:raise ValueError("Planning-package finding not found")
 reviewer_comment=(comment or "").strip() or None
 if disposition in {"Resolved","Accepted / Explained","Not Applicable"} and not reviewer_comment:
  raise ValueError("A reviewer comment is required to close a planning-package finding")
 row.disposition=disposition;row.reviewer_comment=reviewer_comment
 row.status="Open" if disposition in {"To Be Revised","Escalate"} else "Closed"
 row.reviewed_by=user_id;row.reviewed_at=datetime.now(timezone.utc)
 db.commit();db.refresh(row)
 return {"id":row.id,"status":row.status,"disposition":row.disposition,"reviewer_comment":row.reviewer_comment}
