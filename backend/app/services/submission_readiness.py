import csv
import io
import zipfile
import re
from datetime import datetime,timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidClauseRiskFinding,BidPreparedArtifact,DrawingBoqFinding,PlanningPackageFinding
from app.services.estimation_readiness import calculate_estimation_readiness
from app.services.submission_format_intelligence import detect_submission_formats
from app.storage.base import StorageProvider


def _safe_zip_name(value:str)->str:
    safe=re.sub(r"[^A-Za-z0-9._ -]+","_",value).strip(" .")
    return safe[:180] or "artifact"


def submission_readiness(db:Session,bid_id:int):
    detected=detect_submission_formats(db,bid_id)
    artifacts=db.scalars(select(BidPreparedArtifact).where(
        BidPreparedArtifact.bid_project_id==bid_id
    ).order_by(BidPreparedArtifact.template_document_id,BidPreparedArtifact.version_no.desc())).all()

    latest_by_template={}
    approved_by_template={}
    for artifact in artifacts:
        latest_by_template.setdefault(artifact.template_document_id,artifact)
        if artifact.status=="Approved":
            approved_by_template.setdefault(artifact.template_document_id,artifact)

    formats=[]
    blockers=[]
    warnings=[]
    for item in detected["items"]:
        template_id=item.get("template_document_id")
        latest=latest_by_template.get(template_id) if template_id else None
        approved=approved_by_template.get(template_id) if template_id else None

        if not template_id:
            status="Template Missing"
        elif approved:
            status="Approved"
        elif latest and latest.status=="Ready for Review":
            status="Awaiting Approval"
        elif latest:
            status=latest.status
        else:
            status="Not Prepared"

        row={
            "requirement_id":item["requirement_id"],
            "format_name":item["format_name"],
            "format_kind":item["format_kind"],
            "mandatory":item["mandatory"],
            "priority":item["priority"],
            "template_document_id":template_id,
            "template_document":item.get("template_document"),
            "status":status,
            "latest_artifact_id":latest.id if latest else None,
            "latest_version":latest.version_no if latest else None,
            "approved_artifact_id":approved.id if approved else None,
            "approved_version":approved.version_no if approved else None,
        }
        formats.append(row)

        message=f'{item["format_name"]}: {status}'
        if status!="Approved":
            blockers.append(message)

    estimation=calculate_estimation_readiness(db,bid_id)
    if estimation["grade"]!="Ready":
        warnings.append(f'Estimation readiness is {estimation["overall_score"]}% ({estimation["grade"]}).')

    clause_risks=db.scalars(select(BidClauseRiskFinding).where(
        BidClauseRiskFinding.bid_project_id==bid_id,
        BidClauseRiskFinding.review_status!="Closed",
    )).all()
    critical_clause_risks=[x for x in clause_risks if x.severity=="Critical"]
    high_clause_risks=[x for x in clause_risks if x.severity=="High"]
    for risk in critical_clause_risks:
        blockers.append(f'Critical clause risk unresolved: {risk.risk_title}' + (f' (Cl. {risk.source_clause})' if risk.source_clause else ''))
    for risk in high_clause_risks:
        warnings.append(f'High clause risk awaiting Contracts disposition: {risk.risk_title}')

    drawing_findings=db.scalars(select(DrawingBoqFinding).where(
        DrawingBoqFinding.bid_project_id==bid_id,
        DrawingBoqFinding.review_status=="Open",
    )).all()
    planning_findings=db.scalars(select(PlanningPackageFinding).where(
        PlanningPackageFinding.bid_project_id==bid_id,
        PlanningPackageFinding.status=="Open",
    )).all()
    planning_blockers=[x for x in planning_findings if x.severity=="High"]
    planning_warnings=[x for x in planning_findings if x.severity=="Medium"]
    drawing_blockers=[x for x in drawing_findings if x.finding_status in {"Quantity Variance","No BOQ Match"}]
    drawing_warnings=[x for x in drawing_findings if x.finding_status in {"Unit Review","BOQ Quantity Unavailable"}]
    for finding in drawing_blockers:
        blockers.append(f'Drawing/BOQ review unresolved: {finding.finding_status}' + (f' ({finding.boq_reference})' if finding.boq_reference else ''))
    for finding in drawing_warnings:
        warnings.append(f'Drawing/BOQ review required: {finding.finding_status}' + (f' ({finding.boq_reference})' if finding.boq_reference else ''))

    for finding in planning_blockers:
        blockers.append(f'Planning package unresolved: {finding.title}' + (f' ({finding.task_code})' if finding.task_code else ''))
    for finding in planning_warnings:
        warnings.append(f'Planning package review required: {finding.title}' + (f' ({finding.task_code})' if finding.task_code else ''))

    if not detected["items"]:
        warnings.append("No employer-prescribed submission formats were detected automatically; manual tender-package confirmation is required.")

    approved_current=list(approved_by_template.values())
    ready=len(blockers)==0 and bool(detected["items"])

    return {
        "ready":ready,
        "grade":"Ready for Packaging" if ready else "Not Ready",
        "formats":formats,
        "blockers":blockers,
        "warnings":warnings,
        "approved_artifacts":[{
            "id":x.id,
            "artifact_name":x.artifact_name,
            "template_name":x.template_name,
            "version_no":x.version_no,
            "checksum":x.checksum,
            "file_size":x.file_size,
            "approved_at":x.approved_at,
        } for x in approved_current],
        "summary":{
            "detected_formats":len(formats),
            "mandatory_formats":sum(1 for x in formats if x["mandatory"]),
            "approved_formats":sum(1 for x in formats if x["status"]=="Approved"),
            "format_blockers":sum(1 for x in formats if x["status"]!="Approved"),
            "mandatory_blockers":sum(1 for x in formats if x["mandatory"] and x["status"]!="Approved"),
            "warnings":len(warnings),
            "approved_artifacts":len(approved_current),
            "critical_clause_risk_blockers":len(critical_clause_risks),
            "high_clause_risk_warnings":len(high_clause_risks),
            "drawing_boq_blockers":len(drawing_blockers),
            "drawing_boq_warnings":len(drawing_warnings),
            "intelligence_blockers":len(critical_clause_risks)+len(drawing_blockers),
            "planning_package_blockers":len(planning_blockers),
            "planning_package_warnings":len(planning_warnings),
            "total_blockers":len(blockers),
        },
        "estimation_readiness":{
            "overall_score":estimation["overall_score"],
            "grade":estimation["grade"],
        },
        "version":"phase5-submission-readiness-v4",
    }


def build_submission_package(db:Session,bid_id:int,storage:StorageProvider):
    readiness=submission_readiness(db,bid_id)
    if not readiness["ready"]:
        raise ValueError("Submission package cannot be generated while submission-readiness blockers remain unresolved")

    artifact_ids=[x["id"] for x in readiness["approved_artifacts"]]
    artifacts=db.scalars(select(BidPreparedArtifact).where(
        BidPreparedArtifact.id.in_(artifact_ids)
    ).order_by(BidPreparedArtifact.artifact_name)).all() if artifact_ids else []

    output=io.BytesIO()
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as archive:
        manifest_buffer=io.StringIO()
        writer=csv.writer(manifest_buffer)
        writer.writerow(["Artifact ID","Artifact Name","Template","Version","Checksum SHA-256","File Size","Approved At"])
        used_names=set()
        for item in artifacts:
            safe_name=_safe_zip_name(item.artifact_name)
            base=f"{safe_name}.xlsx"
            filename=base
            counter=2
            while filename.lower() in used_names:
                filename=f"{safe_name}_{counter}.xlsx";counter+=1
            used_names.add(filename.lower())
            archive.writestr(filename,storage.read(item.storage_path))
            writer.writerow([
                item.id,item.artifact_name,item.template_name or "",item.version_no,item.checksum,item.file_size,
                item.approved_at.isoformat() if item.approved_at else "",
            ])
        archive.writestr("submission_manifest.csv",manifest_buffer.getvalue().encode("utf-8-sig"))
        archive.writestr("README.txt",(
            "Controlled submission package generated by L&T Bid Intelligence.\n"
            f"Generated at: {datetime.now(timezone.utc).isoformat()}\n"
            f"Bid project ID: {bid_id}\n"
            f"Approved artifacts: {len(artifacts)}\n"
            "Each artifact checksum is listed in submission_manifest.csv.\n"
        ).encode("utf-8"))

    return output.getvalue(),{
        "artifact_count":len(artifacts),
        "artifact_ids":[x.id for x in artifacts],
        "package_version":"phase5-submission-package-v1",
    }
