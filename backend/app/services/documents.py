import hashlib, mimetypes, uuid
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import AuditEvent, BidDocument
from app.storage.base import LocalSecureStorage
def upload_document(db:Session,project_id:int,filename:str,content_type:str|None,content:bytes,user_id:int):
    cfg=get_settings(); safe=Path(filename).name; ext=Path(safe).suffix.lower().lstrip(".")
    if not safe or ext not in cfg.allowed_extensions: raise HTTPException(415,f"Unsupported file type: .{ext or 'none'}")
    if len(content)>cfg.max_file_size_mb*1024*1024: raise HTTPException(413,"File exceeds configured size limit")
    checksum=hashlib.sha256(content).hexdigest(); duplicate=db.scalar(select(BidDocument).where(BidDocument.bid_project_id==project_id,BidDocument.checksum==checksum,BidDocument.document_status!="Archived"))
    doc=BidDocument(bid_project_id=project_id,original_filename=safe,file_extension=ext,mime_type=content_type or mimetypes.guess_type(safe)[0] or "application/octet-stream",file_size=len(content),checksum=checksum,uploaded_by=user_id,document_status="Duplicate" if duplicate else "Needs Review",duplicate_of_document_id=duplicate.id if duplicate else None,information_tags=[])
    if not duplicate:
        stored=f"{uuid.uuid4().hex}.{ext}"; doc.stored_filename=stored; doc.storage_path=LocalSecureStorage(cfg.storage_root).save(project_id,stored,content)
    db.add(doc); db.flush(); db.add(AuditEvent(user_id=user_id,event_type="document.uploaded",entity_type="BidDocument",entity_id=str(doc.id),details={"duplicate":bool(duplicate),"filename":safe})); db.commit(); return doc

