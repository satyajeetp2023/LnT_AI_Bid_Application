def build_planning_readiness(schedule:dict,scope:dict,planning_package:dict,findings:dict):
    blockers=[];warnings=[];passes=[]

    scope_summary=scope.get("summary",{})
    blocking_scope=int(scope_summary.get("blocking") or 0)
    possible_scope=int(scope_summary.get("possible_match") or 0)
    if blocking_scope:
        blockers.append(f"{blocking_scope} expected schedule scope item(s) remain blocking.")
    else:
        passes.append("Expected mandatory schedule scope has no unresolved blocker.")
    if possible_scope:
        warnings.append(f"{possible_scope} expected scope item(s) remain Possible Match and need planner confirmation.")

    alignment=schedule.get("tender_alignment",{})
    alignment_summary=alignment.get("summary",{})
    failed=int(alignment_summary.get("failed") or 0)
    manual=int(alignment_summary.get("manual_review") or 0)
    if failed:
        blockers.append(f"{failed} tender schedule requirement check(s) fail against the uploaded programme.")
    elif alignment_summary.get("schedule_requirements",0):
        passes.append("No automatically checked tender schedule requirement currently fails.")
    if manual:
        warnings.append(f"{manual} tender schedule requirement check(s) still require manual review.")

    strategy=planning_package.get("resource_strategy",{})
    mode=strategy.get("mode")
    if mode=="No Resource Basis Available":
        blockers.append("No resource basis is available from the schedule or a separate bidder resource/equipment plan.")
    elif mode=="Partially Schedule Loaded":
        blockers.append("The schedule is only partially resource-loaded and no separate resource/equipment plan fills the gap.")
    elif mode:
        passes.append(f"Resource basis available: {mode}.")

    staff=planning_package.get("staff_plan",{})
    missing_staff=staff.get("missing_contract_required_roles",[]) or []
    if missing_staff:
        blockers.append("Contract-required staff roles missing from Staff Plan: "+", ".join(missing_staff)+".")
    elif staff.get("contract_required_roles"):
        passes.append("Contract-required staff roles are identifiable in the bidder Staff Plan.")
    elif strategy.get("staff_entries",0):
        passes.append("Bidder Staff Plan is available; no explicit contractual role gap has been identified.")
    else:
        warnings.append("No Staff Plan is currently available for deployment review.")

    feasibility=planning_package.get("resource_feasibility",{})
    shortfalls=int(feasibility.get("productivity_shortfalls") or 0)
    concurrency=len(feasibility.get("concurrency_reviews",[]) or [])
    if shortfalls:
        blockers.append(f"{shortfalls} bidder productivity check(s) are below the BOQ/schedule implied daily requirement.")
    if concurrency:
        warnings.append(f"{concurrency} concurrent resource deployment review(s) require capacity/sharing confirmation.")
    else:
        passes.append("No same-label concurrent resource deployment conflict is currently identified.")

    open_findings=[x for x in findings.get("items",[]) if x.get("status")=="Open"]
    high_findings=[x for x in open_findings if x.get("severity")=="High"]
    medium_findings=[x for x in open_findings if x.get("severity")=="Medium"]
    if high_findings:
        blockers.append(f"{len(high_findings)} High integrated planning finding(s) remain open.")
    if medium_findings:
        warnings.append(f"{len(medium_findings)} Medium integrated planning finding(s) remain open.")

    health=schedule.get("health",{})
    health_grade=health.get("grade")
    if health_grade=="Poor":
        warnings.append(f"Schedule health screening is {health.get('score')}% ({health_grade}); review logic/data-quality issues before final submission.")
    elif health_grade:
        passes.append(f"Schedule health screening: {health.get('score')}% ({health_grade}).")

    source=schedule.get("source_ingestion",{})
    capabilities=source.get("capabilities",{})
    if not capabilities.get("activities",True):
        blockers.append("The uploaded source does not expose a reliable structured activity table.")
    unavailable=[k for k,v in capabilities.items() if not v and k in {"logic","float","calendars"}]
    if unavailable:
        warnings.append("Some planning checks are limited because the source does not provide: "+", ".join(unavailable)+".")

    grade="Not Ready" if blockers else "Needs Attention" if warnings else "Ready"
    return {
        "grade":grade,
        "blockers":blockers,
        "warnings":warnings,
        "passes":passes,
        "summary":{
            "blockers":len(blockers),"warnings":len(warnings),"passes":len(passes),
            "open_high_findings":len(high_findings),"open_medium_findings":len(medium_findings),
            "scope_blockers":blocking_scope,"tender_failures":failed,
            "productivity_shortfalls":shortfalls,"missing_contract_staff_roles":len(missing_staff),
        },
        "methodology":"integrated-planning-readiness-v1",
        "note":"Readiness is rule-based and evidence-driven. It does not invent productivity, staffing or equipment norms and does not replace planner approval.",
    }
