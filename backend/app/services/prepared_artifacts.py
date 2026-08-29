from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session

from app.models import AuditEvent,BidDocument,BidPreparedArtifact
from app.storage.base import StorageProvider


def artifact_dict(item:BidPreparedArtifact):
    return {
        "id":item.id,
        "bid_project_id":item.bid_project_id,
        "template_document_id":item.template_document_id,
        "template_name":item.template_name,
        "artifact_name":item.artifact_name,
        "artifact_type":item.artifact_type,
        "file_extension":item.file_extension,
        "file_size":item.file_size,
        "checksum":item.checksum,
        "version_no":item.version_no,
        "status":item.status,
        "generation_summary":item.generation_summary or {},
        "notes":item.notes,
        "created_by":item.created_by,
        "created_at":item.created_at,
        "updated_at":item.updated_at,
        "ready_for_review_by":item.ready_for_review_by,
        "ready_for_review_at":item.ready_for_review_at,
        "approved_by":item.approved_by,
        "approved_at":item.approved_at,
    }


def create_prepared_artifact(
    db:Session,
    template:BidDocument,
    data:bytes,
    generation_summary:dict,
    storage:StorageProvider,
    user_id:int,
    request_metadata:dict,
):
    current=db.scalar(select(func.max(BidPreparedArtifact.version_no)).where(
        BidPreparedArtifact.bid_project_id==template.bid_project_id,
        BidPreparedArtifact.template_document_id==template.id,
    )) or 0
    version=int(current)+1
    stem=Path(template.original_filename).stem
    stored_filename=f"{stem}_prepared_v{version}_{uuid4().hex[:8]}.xlsx"
    storage_path=storage.save(template.bid_project_id,stored_filename,data)
    compact={k:v for k,v in generation_summary.items() if k not in {"written","unresolved"}}
    item=BidPreparedArtifact(
        bid_project_id=template.bid_project_id,
        template_document_id=template.id,
        artifact_name=f"{stem} - Prepared v{version}",
        artifact_type="Employer Template",
        file_extension="xlsx",
        storage_path=storage_path,
        checksum=sha256(data).hexdigest(),
        file_size=len(data),
        version_no=version,
        status="Draft",
        generation_summary=compact,
        created_by=user_id,
    )
    db.add(item);db.flush()
    db.add(AuditEvent(
        user_id=user_id,bid_project_id=template.bid_project_id,
        event_type="prepared_artifact.created",entity_type="BidPreparedArtifact",entity_id=str(item.id),
        request_metadata=request_metadata,
        details={"template_document_id":template.id,"version_no":version,"checksum":item.checksum,"file_size":len(data)},
    ))
    db.commit();db.refresh(item)
    return item


def list_prepared_artifacts(db:Session,bid_id:int):
    return db.scalars(select(BidPreparedArtifact).where(
        BidPreparedArtifact.bid_project_id==bid_id
    ).order_by(BidPreparedArtifact.template_document_id,BidPreparedArtifact.version_no.desc())).all()


def get_prepared_artifact(db:Session,artifact_id:int):
    item=db.get(BidPreparedArtifact,artifact_id)
    if not item:raise HTTPException(404,"Prepared artifact not found")
    return item


def mark_artifact_ready(db:Session,item:BidPreparedArtifact,user_id:int,request_metadata:dict):
    if item.status!="Draft":raise HTTPException(422,"Only Draft prepared artifacts can be sent for review")
    item.status="Ready for Review"
    item.ready_for_review_by=user_id
    item.ready_for_review_at=datetime.now(timezone.utc)
    db.add(AuditEvent(
        user_id=user_id,bid_project_id=item.bid_project_id,
        event_type="prepared_artifact.ready_for_review",entity_type="BidPreparedArtifact",entity_id=str(item.id),
        request_metadata=request_metadata,details={"version_no":item.version_no},
    ))
    db.commit();db.refresh(item);return item


def approve_artifact(db:Session,item:BidPreparedArtifact,user_id:int,request_metadata:dict):
    if item.status!="Ready for Review":raise HTTPException(422,"Only prepared artifacts Ready for Review can be approved")
    previous=db.scalars(select(BidPreparedArtifact).where(
        BidPreparedArtifact.bid_project_id==item.bid_project_id,
        BidPreparedArtifact.template_document_id==item.template_document_id,
        BidPreparedArtifact.status=="Approved",
        BidPreparedArtifact.id!=item.id,
    )).all()
    for old in previous:
        old.status="Superseded"
    item.status="Approved"
    item.approved_by=user_id
    item.approved_at=datetime.now(timezone.utc)
    db.add(AuditEvent(
        user_id=user_id,bid_project_id=item.bid_project_id,
        event_type="prepared_artifact.approved",entity_type="BidPreparedArtifact",entity_id=str(item.id),
        request_metadata=request_metadata,
        details={"version_no":item.version_no,"superseded_artifact_ids":[x.id for x in previous]},
    ))
    db.commit();db.refresh(item);return item
