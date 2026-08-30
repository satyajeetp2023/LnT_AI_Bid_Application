import hashlib,mimetypes,uuid
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import func,or_,select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import AuditEvent,BidDocument
from app.services.document_classification import auto_classify_document
from app.services.document_taxonomy import DOCUMENT_CATEGORIES
from app.storage.base import LocalSecureStorage
def audit(db,user_id,project_id,event,doc,metadata=None,details=None): db.add(AuditEvent(user_id=user_id,bid_project_id=project_id,event_type=event,entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata or {},details=details or {}))
def upload_document(db:Session,project_id:int,filename:str,content_type:str|None,content:bytes,user_id:int):
 cfg=get_settings(); safe=Path(filename).name; ext=Path(safe).suffix.lower().lstrip(".")
 if not safe or ext not in cfg.allowed_extensions: raise HTTPException(415,f"Unsupported file type: .{ext or 'none'}")
 if content.startswith(b"MZ") or content.startswith(b"\x7fELF"): raise HTTPException(415,"Executable content is not permitted in tender document uploads")
 if len(content)>cfg.max_file_size_mb*1024*1024: raise HTTPException(413,"File exceeds configured size limit")
 checksum=hashlib.sha256(content).hexdigest(); duplicate=db.scalar(select(BidDocument).where(BidDocument.bid_project_id==project_id,BidDocument.checksum==checksum,BidDocument.document_status!="Archived"))
 doc=BidDocument(bid_project_id=project_id,original_filename=safe,file_extension=ext,mime_type=content_type or mimetypes.guess_type(safe)[0] or "application/octet-stream",file_size=len(content),checksum=checksum,uploaded_by=user_id,document_status="Duplicate" if duplicate else "Needs Review",classification_status="pending",is_latest_version=True,duplicate_of_document_id=duplicate.id if duplicate else None,information_tags=[])
 if not duplicate:
  stored=f"{uuid.uuid4().hex}.{ext}"; doc.stored_filename=stored; doc.storage_path=LocalSecureStorage(cfg.storage_root).save(project_id,stored,content)
 db.add(doc); db.flush(); audit(db,user_id,project_id,"document.uploaded",doc,details={"duplicate":bool(duplicate),"filename":safe}); db.commit()
 if not duplicate: auto_classify_document(db,doc,LocalSecureStorage(cfg.storage_root),user_id)
 return doc
def classify(db,doc,category,subcategory,tags,user_id,metadata):
 if category not in DOCUMENT_CATEGORIES: raise HTTPException(422,"Unsupported document category")
 doc.document_category=category; doc.document_subcategory=subcategory; doc.information_tags=list(dict.fromkeys(tags)); doc.document_status="Needs Review" if category=="Other" else "Uploaded"; doc.classification_status="manually_classified"; audit(db,user_id,doc.bid_project_id,"document.reclassified",doc,metadata,{"category":category,"tags":doc.information_tags}); db.commit(); return doc
def update_document_metadata(db,doc,payload,user_id,request_metadata):
 values=payload.model_dump(exclude_unset=True)
 category=values.get("document_category")
 if category is not None and category not in DOCUMENT_CATEGORIES: raise HTTPException(422,"Unsupported document category")
 for field,value in values.items(): setattr(doc,field,value)
 if category is not None: doc.classification_status="manually_classified"
 audit(db,user_id,doc.bid_project_id,"document.metadata_updated",doc,request_metadata,{"fields":list(values),"category":category})
 db.commit(); return doc
def update_notes(db,doc,notes,user_id,metadata): doc.notes=notes; audit(db,user_id,doc.bid_project_id,"document.notes_updated",doc,metadata); db.commit(); return doc
def archive(db,doc,user_id,metadata): doc.document_status="Archived"; doc.is_latest_revision=False; audit(db,user_id,doc.bid_project_id,"document.archived",doc,metadata); db.commit(); return doc
def mark_revision(db,doc,original,user_id,metadata):
 if doc.id==original.id or doc.bid_project_id!=original.bid_project_id: raise HTTPException(422,"Invalid revision relationship")
 ancestor=original
 seen={doc.id}
 while ancestor:
  if ancestor.id in seen: raise HTTPException(422,"Circular revision relationship")
  seen.add(ancestor.id); ancestor=db.get(BidDocument,ancestor.revision_of_document_id) if ancestor.revision_of_document_id else None
 root=original
 while root.revision_of_document_id: root=db.get(BidDocument,root.revision_of_document_id)
 family=db.scalars(select(BidDocument).where(BidDocument.bid_project_id==doc.bid_project_id,or_(BidDocument.id==root.id,BidDocument.revision_of_document_id==root.id))).all()
 for item in family: item.is_latest_revision=False
 doc.revision_of_document_id=root.id; doc.revision_no=max([x.revision_no for x in family]+[0])+1; doc.is_latest_revision=True; audit(db,user_id,doc.bid_project_id,"document.revision_created",doc,metadata,{"revision_of":root.id,"revision_no":doc.revision_no}); db.commit(); return doc
