import calendar
import math
import re
from collections import Counter,defaultdict
from datetime import date,datetime,timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidRequirement,PlanningPackageFinding,PlanningResourceEntry,ScheduleScopeItem


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


def _boq_quantity(item):
 text=str(item.source_excerpt or "")
 match=re.search(r"\|\s*Qty:\s*([0-9,]+(?:\.\d+)?)\s*([^|]*)",text,re.I)
 if not match:return None,None
 try:quantity=float(match.group(1).replace(",",""))
 except ValueError:return None,None
 unit=(match.group(2) or "").strip() or None
 return quantity,unit


def _unit_norm(value):
 text=re.sub(r"[^a-z0-9]+"," ",str(value or "").lower()).strip()
 mapping={
  "no":"nos","nos":"nos","number":"nos","numbers":"nos","each":"nos",
  "m":"m","meter":"m","meters":"m","metre":"m","metres":"m",
  "km":"km","kilometer":"km","kilometre":"km",
  "m2":"m2","sqm":"m2","sq m":"m2",
  "m3":"m3","cum":"m3","cu m":"m3",
 }
 return mapping.get(text,text)


def _productivity_capacity(entry):
 if entry.productivity_rate is None:return None
 rate=float(entry.productivity_rate)
 text=str(entry.productivity_unit or "").lower()
 base=re.split(r"/|\bper\b",text,1)[0].strip()
 base_unit=_unit_norm(base)
 per_resource=any(x in text for x in ("crew","gang","resource","equipment","machine","plant","team"))
 quantity=float(entry.quantity) if entry.quantity is not None else None
 if per_resource and quantity is not None:
  return {"capacity_per_day":rate*quantity,"base_unit":base_unit,"basis":"Per Resource × Quantity","rate":rate,"resource_quantity":quantity}
 if per_resource:
  return {"capacity_per_day":None,"base_unit":base_unit,"basis":"Per Resource / Quantity Missing","rate":rate,"resource_quantity":quantity}
 return {"capacity_per_day":rate,"base_unit":base_unit,"basis":"Total Planned Rate","rate":rate,"resource_quantity":quantity}


def _overlap(a_start,a_finish,b_start,b_finish):
 return bool(a_start and a_finish and b_start and b_finish and a_start<=b_finish and b_start<=a_finish)


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

 boq_items=db.scalars(select(ScheduleScopeItem).where(
  ScheduleScopeItem.bid_project_id==bid_id,
  ScheduleScopeItem.source_type=="BOQ",
  ScheduleScopeItem.parent_id.is_(None),
 )).all()
 productivity_checks=[]
 for boq in boq_items:
  boq_qty,boq_unit=_boq_quantity(boq)
  if boq_qty is None or not boq_unit:continue
  ranked=sorted(((_score(boq.activity_name,f"{task.get('task_code','')} {task.get('task_name','')}"),task) for task in tasks),key=lambda x:-x[0])
  match_score,task=(ranked[0] if ranked else (0.0,None))
  if not task or match_score<.34:continue
  duration_hours=max(float(task.get("target_drtn_hr_cnt") or 0),float(task.get("remain_drtn_hr_cnt") or 0))
  if duration_hours<=0:continue
  duration_days=duration_hours/8.0
  required_rate=boq_qty/duration_days
  plan_entries=[x for x in mapped_external.get(task.get("task_id"),[]) if x.productivity_rate is not None]
  comparisons=[]
  for entry in plan_entries:
   capacity=_productivity_capacity(entry)
   if not capacity:continue
   if not entry.productivity_unit:
    status="Rate Unit Missing";variance=None
   elif capacity["base_unit"] and _unit_norm(boq_unit)!=capacity["base_unit"]:
    status="Unit Review";variance=None
   elif capacity["capacity_per_day"] is None:
    status="Resource Quantity Missing";variance=None
   else:
    variance=capacity["capacity_per_day"]-required_rate
    status="Meets / Exceeds Implied Requirement" if variance>=0 else "Below Implied Requirement"
   resolution_options=[]
   minimum_resource_quantity=None;additional_resource_quantity=None
   required_duration_days=None;duration_extension_days=None;productivity_increase_percent=None
   if capacity["capacity_per_day"] is not None and capacity["capacity_per_day"]>0:
    required_duration_days=boq_qty/capacity["capacity_per_day"]
    duration_extension_days=max(0.0,required_duration_days-duration_days)
   if status=="Below Implied Requirement":
    if capacity["basis"]=="Per Resource × Quantity" and capacity["rate"]>0 and capacity["resource_quantity"] is not None:
     minimum_resource_quantity=math.ceil(required_rate/capacity["rate"])
     additional_resource_quantity=max(0,minimum_resource_quantity-math.floor(capacity["resource_quantity"]))
     resolution_options.append(f"Test increasing {entry.resource_name} quantity from {capacity['resource_quantity']:g} to at least {minimum_resource_quantity} at the bidder-stated per-resource rate.")
    if required_duration_days is not None:
     resolution_options.append(f"At the currently stated capacity, test a duration of about {required_duration_days:.2f} equivalent working days instead of {duration_days:.2f}.")
    if capacity["capacity_per_day"]>0:
     productivity_increase_percent=max(0.0,(required_rate-capacity["capacity_per_day"])*100/capacity["capacity_per_day"])
     resolution_options.append(f"To retain the current duration, the stated total output would need to increase by about {productivity_increase_percent:.1f}%.")
   comparisons.append({
    "resource_entry_id":entry.id,"resource_name":entry.resource_name,
    "productivity_rate":capacity["rate"],"productivity_unit":entry.productivity_unit,
    "resource_quantity":capacity["resource_quantity"],"basis":capacity["basis"],
    "available_capacity_per_day":round(capacity["capacity_per_day"],4) if capacity["capacity_per_day"] is not None else None,
    "status":status,"capacity_variance_per_day":round(variance,4) if variance is not None else None,
    "minimum_resource_quantity":minimum_resource_quantity,
    "additional_resource_quantity":additional_resource_quantity,
    "required_duration_days":round(required_duration_days,2) if required_duration_days is not None else None,
    "duration_extension_days":round(duration_extension_days,2) if duration_extension_days is not None else None,
    "productivity_increase_percent":round(productivity_increase_percent,1) if productivity_increase_percent is not None else None,
    "resolution_options":resolution_options,
   })
  productivity_checks.append({
   "boq_scope_item_id":boq.id,"boq_reference":boq.source_reference,
   "boq_activity":boq.activity_name,"boq_quantity":boq_qty,"boq_unit":boq_unit,
   "task_code":task.get("task_code"),"task_name":task.get("task_name"),"match_score":match_score,
   "duration_hours":round(duration_hours,2),"equivalent_working_days":round(duration_days,2),
   "required_implied_rate_per_day":round(required_rate,4),
   "comparisons":comparisons,
   "status":"No Bidder Productivity Rate" if not comparisons else (
    "Review Required" if any(x["status"] in {"Below Implied Requirement","Unit Review","Resource Quantity Missing","Rate Unit Missing"} for x in comparisons)
    else "Internally Consistent"
   ),
   "note":"Required rate is BOQ quantity divided by scheduled duration using an 8-hour equivalent working day. It is checked only against productivity explicitly stated by the bidder.",
  })

 matched_with_dates=[]
 for row in external_matches:
  if row.get("match_status") not in {"Matched","Possible Match"}:continue
  start=_date(row.get("activity_start"));finish=_date(row.get("activity_finish"))
  if not start or not finish:continue
  matched_with_dates.append((row,start,finish))
 task_by_code={str(x.get("task_code") or ""):x for x in tasks if x.get("task_code")}
 concurrency_reviews=[]
 for i,(left,l_start,l_finish) in enumerate(matched_with_dates):
  for right,r_start,r_finish in matched_with_dates[i+1:]:
   if left.get("matched_task_code")==right.get("matched_task_code"):continue
   if _norm(left.get("resource_name"))!=_norm(right.get("resource_name")):continue
   if not _overlap(l_start,l_finish,r_start,r_finish):continue
   exact_identifier=bool(re.search(r"\d",str(left.get("resource_name") or "")))
   overlap_days=(min(l_finish,r_finish)-max(l_start,r_start)).days+1
   left_task=task_by_code.get(str(left.get("matched_task_code") or ""))
   right_task=task_by_code.get(str(right.get("matched_task_code") or ""))
   def tf_days(task):
    if not task or not capabilities.get("float"):return None
    try:return max(0.0,float(task.get("total_float_hr_cnt"))/8.0)
    except (TypeError,ValueError):return None
   left_float=tf_days(left_task);right_float=tf_days(right_task)
   candidates=[
    (left.get("matched_task_code"),left.get("matched_task_name"),left_float),
    (right.get("matched_task_code"),right.get("matched_task_name"),right_float),
   ]
   candidates=[x for x in candidates if x[2] is not None and x[2]>0]
   candidates.sort(key=lambda x:-x[2])
   resequence_suggestion=None
   if candidates:
    code,name,float_days=candidates[0]
    resequence_suggestion=f"Test shifting {code} by up to {min(float_days,overlap_days):.2f} equivalent working days within its current total-float allowance, then recalculate the programme."
   concurrency_reviews.append({
    "resource_name":left.get("resource_name"),
    "left_task_code":left.get("matched_task_code"),"left_task_name":left.get("matched_task_name"),
    "right_task_code":right.get("matched_task_code"),"right_task_name":right.get("matched_task_name"),
    "overlap_start":max(l_start,r_start).isoformat(),"overlap_finish":min(l_finish,r_finish).isoformat(),
    "overlap_days":overlap_days,
    "left_total_float_days":round(left_float,2) if left_float is not None else None,
    "right_total_float_days":round(right_float,2) if right_float is not None else None,
    "resequence_suggestion":resequence_suggestion,
    "severity":"High" if exact_identifier else "Medium",
    "status":"Potential Double Booking" if exact_identifier else "Concurrent Resource Review",
    "note":"Same resource label is deployed against overlapping activities. Confirm whether this represents one shared resource or separate available units. Any float-based shift is a test suggestion only and must be recalculated in the scheduling tool.",
   })

 def month_start(value:date):
  return date(value.year,value.month,1)
 def next_month(value:date):
  return date(value.year+1,1,1) if value.month==12 else date(value.year,value.month+1,1)
 dated_entries=[x for x in entries if x.start_date or x.finish_date]
 profile_rows=[]
 if task_dates:
  horizon_start=month_start(min(task_dates))
  horizon_finish=month_start(max(task_dates))
 elif dated_entries:
  starts=[x.start_date or x.finish_date for x in dated_entries if x.start_date or x.finish_date]
  finishes=[x.finish_date or x.start_date for x in dated_entries if x.start_date or x.finish_date]
  horizon_start=month_start(min(starts));horizon_finish=month_start(max(finishes))
 else:
  horizon_start=horizon_finish=None
 cursor=horizon_start
 months=0
 while cursor and horizon_finish and cursor<=horizon_finish and months<120:
  month_end=date(cursor.year,cursor.month,calendar.monthrange(cursor.year,cursor.month)[1])
  active=[x for x in entries if (x.start_date is None or x.start_date<=month_end) and (x.finish_date is None or x.finish_date>=cursor) and (x.start_date or x.finish_date)]
  totals={}
  for category in ("Staff","Labour","Equipment","Other"):
   rows=[x for x in active if x.resource_category==category]
   totals[category]=round(sum(float(x.quantity) for x in rows if x.quantity is not None),2)
  profile_rows.append({
   "month":cursor.strftime("%Y-%m"),
   "staff":totals["Staff"],"labour":totals["Labour"],"equipment":totals["Equipment"],"other":totals["Other"],
   "active_entries":len(active),
  })
  cursor=next_month(cursor);months+=1
 peaks={}
 for category,key in (("Staff","staff"),("Labour","labour"),("Equipment","equipment"),("Other","other")):
  if not profile_rows:
   peaks[category]={"quantity":0,"month":None}
  else:
   best=max(profile_rows,key=lambda x:x[key])
   peaks[category]={"quantity":best[key],"month":best["month"] if best[key]>0 else None}

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

 productivity_shortfalls=[x for x in productivity_checks if any(y["status"]=="Below Implied Requirement" for y in x["comparisons"])]
 if productivity_shortfalls:
  issues.append({"severity":"High","type":"Productivity Feasibility","message":f"{len(productivity_shortfalls)} BOQ/schedule activity checks require a higher daily output than the bidder-stated resource productivity provides."})
 if concurrency_reviews:
  issues.append({"severity":"Medium","type":"Concurrent Resource Deployment","message":f"{len(concurrency_reviews)} overlapping activity pairs use the same resource label and require sharing/capacity confirmation."})

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
  "time_phased_resource_profile":{
   "months":profile_rows,
   "peaks":peaks,
   "undated_entries":sum(1 for x in entries if not x.start_date and not x.finish_date),
   "horizon_start":horizon_start.isoformat() if horizon_start else None,
   "horizon_finish":horizon_finish.isoformat() if horizon_finish else None,
   "note":"Monthly totals sum only bidder entries with stated quantities and deployment dates. Missing quantities are not guessed.",
  },
  "resource_feasibility":{
   "productivity_checks":productivity_checks,
   "productivity_shortfalls":len(productivity_shortfalls),
   "concurrency_reviews":concurrency_reviews,
   "note":"Feasibility uses only bidder-supplied BOQ, duration, resource quantities and stated productivity. No external productivity norm is assumed.",
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
   "productivity_shortfalls":len(productivity_shortfalls),
   "concurrent_resource_reviews":len(concurrency_reviews),
   "undated_resource_entries":sum(1 for x in entries if not x.start_date and not x.finish_date),
   "high_issues":sum(1 for x in issues if x["severity"]=="High"),
   "medium_issues":sum(1 for x in issues if x["severity"]=="Medium"),
  },
  "version":"integrated-planning-package-v5",
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
 for check in analysis.get("resource_feasibility",{}).get("productivity_checks",[]):
  shortfalls=[x for x in check.get("comparisons",[]) if x.get("status")=="Below Implied Requirement"]
  if not shortfalls:continue
  candidates.append({
   "finding_key":f"productivity:{check.get('boq_scope_item_id')}",
   "finding_type":"Productivity Feasibility","severity":"High",
   "title":"Bidder-stated productivity is below BOQ/schedule implied requirement",
   "description":f"{check.get('boq_reference') or check.get('boq_activity')} requires about {check.get('required_implied_rate_per_day')} {check.get('boq_unit')}/day over the scheduled duration; bidder-stated resource productivity is lower.",
   "task_code":check.get("task_code"),"task_name":check.get("task_name"),
   "source_reference":check.get("boq_reference"),
  })
 for index,review in enumerate(analysis.get("resource_feasibility",{}).get("concurrency_reviews",[])):
  key=f"concurrency:{review.get('resource_name')}:{review.get('left_task_code')}:{review.get('right_task_code')}"
  candidates.append({
   "finding_key":re.sub(r"\s+","-",key.lower())[:300],
   "finding_type":"Concurrent Resource Deployment","severity":review.get("severity") or "Medium",
   "title":review.get("status") or "Concurrent resource deployment review",
   "description":f"{review.get('resource_name')} is shown against overlapping activities {review.get('left_task_code')} and {review.get('right_task_code')} from {review.get('overlap_start')} to {review.get('overlap_finish')}. Confirm whether sufficient separate units are available.",
   "task_code":review.get("left_task_code"),"task_name":review.get("left_task_name"),
   "source_reference":review.get("resource_name"),
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
  "version":"integrated-planning-package-findings-v2",
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
