import re
from datetime import datetime,timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent,BidClauseRiskFinding,BidDocument,ClauseRiskPattern
from app.services.requirement_extraction import RuleBasedRequirementExtractionProvider


DEFAULT_RISKS=(
 {"risk_code":"UNLIMITED_LIABILITY","title":"Unlimited / Uncapped Liability","category":"Liability","severity":"Critical",
  "signals":("unlimited liability","liability shall be unlimited","without limitation of liability","no limitation on liability","liability is not capped"),
  "exclusions":("liability shall not exceed","aggregate liability shall not exceed"),
  "explanation":"The clause may expose the contractor to liability without an agreed monetary cap.",
  "guidance":"Confirm whether an aggregate liability cap applies and identify carve-outs before accepting the clause."},
 {"risk_code":"BROAD_INDEMNITY","title":"Broad Indemnity Obligation","category":"Indemnity","severity":"High",
  "signals":("indemnify and hold harmless","indemnify, defend and hold harmless","against all claims, losses, damages","any and all claims"),
  "exclusions":(),
  "explanation":"The indemnity wording may be broader than direct contractor-caused loss and may extend to third-party or employer-caused exposure.",
  "guidance":"Review trigger, causation standard, third-party scope, negligence allocation and liability cap interaction."},
 {"risk_code":"CONSEQUENTIAL_LOSS","title":"Consequential / Indirect Loss Exposure","category":"Liability","severity":"Critical",
  "signals":("consequential loss","indirect loss","loss of profit","loss of revenue","loss of production"),
  "exclusions":("neither party shall be liable","contractor shall not be liable","excluding consequential"),
  "explanation":"The clause may make the contractor liable for consequential or indirect losses that are normally excluded or capped.",
  "guidance":"Check whether consequential loss is excluded and whether any carve-out is narrowly defined."},
 {"risk_code":"ONE_SIDED_TERMINATION","title":"One-Sided Termination Right","category":"Termination","severity":"High",
  "signals":("terminate for convenience","termination for convenience","employer may terminate at any time","employer shall have the right to terminate"),
  "exclusions":(),
  "explanation":"The employer may have a broad unilateral termination right.",
  "guidance":"Check compensation on termination, demobilization, committed procurement, profit on omitted work and notice period."},
 {"risk_code":"LD_UNCAPPED","title":"Liquidated Damages Without Clear Cap","category":"Delay / LD","severity":"Critical",
  "signals":("liquidated damages","delay damages","damages for delay"),
  "exclusions":("maximum liquidated damages","aggregate liquidated damages shall not exceed","cap on liquidated damages"),
  "explanation":"Delay damages are stated but no clear cap is detected in the same source excerpt.",
  "guidance":"Locate the overall LD cap and confirm whether separate milestone LDs aggregate within that cap."},
 {"risk_code":"LD_MULTIPLE","title":"Multiple / Layered Delay Damages","category":"Delay / LD","severity":"High",
  "signals":("milestone liquidated damages","sectional liquidated damages","interim milestone damages","separate liquidated damages"),
  "exclusions":(),
  "explanation":"Separate milestone or sectional LD mechanisms may create cumulative exposure.",
  "guidance":"Check aggregation rules, overall cap and whether concurrent milestone LDs can be levied together."},
 {"risk_code":"BROAD_SETOFF","title":"Broad Employer Set-Off / Deduction Right","category":"Payment","severity":"High",
  "signals":("set off any amount","set-off any amount","deduct any amount","withhold any amount","recover from any sums due"),
  "exclusions":(),
  "explanation":"The employer may have a broad right to withhold, deduct or set off amounts from certified payments.",
  "guidance":"Check notice, substantiation, dispute rights and whether set-off is limited to amounts finally determined."},
 {"risk_code":"PAYMENT_CONDITIONAL","title":"Conditional / Pay-When-Paid Exposure","category":"Payment","severity":"High",
  "signals":("pay when paid","payment shall be subject to","payment is conditional upon","only after receipt of payment"),
  "exclusions":(),
  "explanation":"Payment entitlement may depend on an external event rather than completed/certified work.",
  "guidance":"Confirm whether payment timing remains objectively measurable and independent of third-party payment."},
 {"risk_code":"WARRANTY_EXTENSION","title":"Extended / Restarting Warranty or DLP","category":"Warranty / DLP","severity":"High",
  "signals":("warranty period shall recommence","defects liability period shall recommence","warranty shall restart","extended defects liability","additional warranty period"),
  "exclusions":(),
  "explanation":"Rectification or replacement may restart or materially extend warranty/DLP exposure.",
  "guidance":"Check whether extension is limited to repaired/replaced parts and subject to an overall long-stop date."},
 {"risk_code":"FITNESS_PURPOSE","title":"Fitness-for-Purpose Design Obligation","category":"Design Liability","severity":"High",
  "signals":("fit for purpose","fitness for purpose","fitness-for-purpose"),
  "exclusions":(),
  "explanation":"Fitness-for-purpose can impose a result-based obligation beyond reasonable skill and care.",
  "guidance":"Check the governing design standard, reliance information and whether professional liability insurance responds."},
 {"risk_code":"EMPLOYER_DISCRETION","title":"Sole / Absolute Employer Discretion","category":"Administration","severity":"Medium",
  "signals":("sole discretion of the employer","absolute discretion of the employer","employer's sole discretion","employer’s sole discretion"),
  "exclusions":(),
  "explanation":"A material contractual decision may be left to unilateral employer discretion.",
  "guidance":"Check whether the discretion is constrained by reasonableness, objective criteria or Engineer determination."},
)


def _norm(text:str)->str:
 return re.sub(r"\s+"," ",str(text or "").lower()).strip()


def ensure_default_risk_library(db:Session):
 existing={x.risk_code:x for x in db.scalars(select(ClauseRiskPattern)).all()}
 created=updated=0
 for spec in DEFAULT_RISKS:
  row=existing.get(spec["risk_code"])
  if row:
   row.title=spec["title"];row.category=spec["category"];row.severity=spec["severity"]
   row.pattern_terms=list(spec["signals"]);row.exclusion_terms=list(spec["exclusions"])
   row.explanation=spec["explanation"];row.reviewer_guidance=spec["guidance"];updated+=1
  else:
   db.add(ClauseRiskPattern(
    risk_code=spec["risk_code"],title=spec["title"],category=spec["category"],severity=spec["severity"],
    pattern_terms=list(spec["signals"]),exclusion_terms=list(spec["exclusions"]),explanation=spec["explanation"],
    reviewer_guidance=spec["guidance"],source_type="Firm Library",
   ));created+=1
 db.commit()
 return {"created":created,"updated":updated}


def _clause_from_text(text:str):
 match=re.match(r"\s*(?:(?:clause|section)\s+)?(\d+(?:\.\d+){1,6})\b",text,re.I)
 return match.group(1) if match else None


def _risk_matches(text:str,pattern:ClauseRiskPattern):
 lower=_norm(text)
 if any(_norm(x) in lower for x in (pattern.exclusion_terms or [])):return False,0.0
 signals=[_norm(x) for x in (pattern.pattern_terms or []) if _norm(x)]
 matched=[x for x in signals if x in lower]
 if not matched:return False,0.0
 confidence=min(.98,.70+.08*len(matched))
 return True,confidence


def scan_document_clause_risks(
 db:Session,document:BidDocument,storage,user_id:int,request_metadata:dict|None=None
):
 if document.duplicate_of_document_id or not document.storage_path:
  raise ValueError("Document content is not available for clause-risk scanning")
 ensure_default_risk_library(db)
 patterns=db.scalars(select(ClauseRiskPattern).where(ClauseRiskPattern.is_active.is_(True))).all()
 provider=RuleBasedRequirementExtractionProvider()
 units=provider.source_units(document.file_extension,storage.read(document.storage_path))
 existing=db.scalars(select(BidClauseRiskFinding).where(
  BidClauseRiskFinding.bid_project_id==document.bid_project_id,
  BidClauseRiskFinding.source_document_id==document.id,
 )).all()
 signatures={(x.risk_code,_norm(x.source_excerpt),x.source_page or "") for x in existing}
 created=0
 for unit in units:
  section=unit.section
  for raw in unit.text.splitlines():
   line=re.sub(r"\s+"," ",raw).strip()
   if len(line)<25:continue
   for pattern in patterns:
    matched,confidence=_risk_matches(line,pattern)
    if not matched:continue
    sig=(pattern.risk_code,_norm(line),str(unit.page or ""))
    if sig in signatures:continue
    db.add(BidClauseRiskFinding(
     bid_project_id=document.bid_project_id,source_document_id=document.id,risk_pattern_id=pattern.id,
     risk_code=pattern.risk_code,risk_title=pattern.title,risk_category=pattern.category,severity=pattern.severity,
     source_page=str(unit.page) if unit.page else None,source_clause=_clause_from_text(line),source_section=section,
     source_excerpt=line[:4000],confidence=Decimal(str(confidence)),detection_method="Firm Risk Pattern",
     review_status="Open",
    ));signatures.add(sig);created+=1
 db.add(AuditEvent(
  user_id=user_id,bid_project_id=document.bid_project_id,event_type="clause_risk.scan_completed",
  entity_type="BidDocument",entity_id=str(document.id),request_metadata=request_metadata or {},
  details={"created":created,"patterns_checked":len(patterns),"scanner_version":"clause-risk-v1"},
 ))
 db.commit()
 return {"document_id":document.id,"created":created,"patterns_checked":len(patterns),"scanner_version":"clause-risk-v1"}


def bid_clause_risk_summary(db:Session,bid_id:int):
 rows=db.scalars(select(BidClauseRiskFinding).where(
  BidClauseRiskFinding.bid_project_id==bid_id
 ).order_by(BidClauseRiskFinding.created_at.desc())).all()
 return {
  "items":[{
   "id":x.id,"source_document_id":x.source_document_id,"risk_code":x.risk_code,"risk_title":x.risk_title,
   "risk_category":x.risk_category,"severity":x.severity,"source_page":x.source_page,"source_clause":x.source_clause,
   "source_section":x.source_section,"source_excerpt":x.source_excerpt,"confidence":float(x.confidence),
   "review_status":x.review_status,"reviewer_disposition":x.reviewer_disposition,"reviewer_comment":x.reviewer_comment,
  } for x in rows],
  "summary":{
   "total":len(rows),
   "critical":sum(1 for x in rows if x.severity=="Critical" and x.review_status!="Closed"),
   "high":sum(1 for x in rows if x.severity=="High" and x.review_status!="Closed"),
   "open":sum(1 for x in rows if x.review_status!="Closed"),
   "accepted":sum(1 for x in rows if x.reviewer_disposition=="Accept Risk"),
   "mitigated":sum(1 for x in rows if x.reviewer_disposition=="Mitigated / Qualified"),
  },
  "version":"clause-risk-v1",
  "note":"AI/rule flags are review prompts, not legal conclusions. Every finding remains source-linked and requires human disposition.",
 }


def review_clause_risk(db:Session,finding_id:int,disposition:str,comment:str|None,user_id:int):
 allowed={"Open","Accept Risk","Mitigated / Qualified","Not Applicable","False Positive","Escalate"}
 if disposition not in allowed:raise ValueError("Unsupported clause-risk disposition")
 finding=db.get(BidClauseRiskFinding,finding_id)
 if not finding:raise ValueError("Clause-risk finding not found")
 finding.reviewer_disposition=disposition
 finding.reviewer_comment=(comment or "").strip() or None
 finding.review_status="Closed" if disposition in {"Accept Risk","Mitigated / Qualified","Not Applicable","False Positive"} else "Open"
 finding.reviewed_by=user_id
 finding.reviewed_at=datetime.now(timezone.utc)
 db.commit();db.refresh(finding)
 return {"id":finding.id,"review_status":finding.review_status,"reviewer_disposition":finding.reviewer_disposition,"reviewer_comment":finding.reviewer_comment}
