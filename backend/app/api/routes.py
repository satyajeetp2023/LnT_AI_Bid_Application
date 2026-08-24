from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Header
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import AuditEvent, BidDocument, User
from app.schemas.bids import BidCreate,BidRead,DocumentRead
from app.security.auth import current_user,require_write
from app.services.bids import create_bid,list_bids
from app.services.documents import upload_document
from app.storage.base import LocalSecureStorage
from app.core.config import get_settings
router=APIRouter()
def user_dep(db:Session=Depends(get_db),x_user_id:int=Header(default=1,alias="X-User-ID")): return current_user(db,x_user_id)
@router.get("/health")
def health(db:Session=Depends(get_db)): db.execute(select(1)); return {"status":"ok","database":"connected"}
@router.get("/auth/me")
def me(user:User=Depends(user_dep)): return {"id":user.id,"name":user.full_name,"roles":[r.name.value for r in user.roles]}
@router.get("/bids",response_model=list[BidRead])
def bids(db:Session=Depends(get_db),user:User=Depends(user_dep)): return list_bids(db)
@router.post("/bids",response_model=BidRead,status_code=201)
def add_bid(payload:BidCreate,db:Session=Depends(get_db),user:User=Depends(user_dep)): require_write(user); return create_bid(db,payload,user.id)
@router.get("/bids/{bid_id}/documents",response_model=list[DocumentRead])
def documents(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)): return db.scalars(select(BidDocument).where(BidDocument.bid_project_id==bid_id).order_by(BidDocument.uploaded_at.desc())).all()
@router.post("/bids/{bid_id}/documents",response_model=list[DocumentRead])
async def upload(bid_id:int,files:list[UploadFile]=File(...),db:Session=Depends(get_db),user:User=Depends(user_dep)):
    require_write(user); cfg=get_settings()
    if len(files)>cfg.max_files_per_batch: raise HTTPException(413,"Too many files in batch")
    result=[]; total=0
    for file in files:
        data=await file.read(); total+=len(data)
        if total>cfg.max_batch_size_mb*1024*1024: raise HTTPException(413,"Batch exceeds configured size limit")
        result.append(upload_document(db,bid_id,file.filename or "",file.content_type,data,user.id))
    return result
@router.get("/documents/{document_id}/download")
def download(document_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    doc=db.get(BidDocument,document_id)
    if not doc or not doc.storage_path: raise HTTPException(404,"Document content not available")
    data=LocalSecureStorage(get_settings().storage_root).read(doc.storage_path); db.add(AuditEvent(user_id=user.id,event_type="document.downloaded",entity_type="BidDocument",entity_id=str(doc.id))); db.commit(); return Response(data,media_type=doc.mime_type,headers={"Content-Disposition":f'attachment; filename="{doc.original_filename}"'})
@router.get("/audit")
def audit(db:Session=Depends(get_db),user:User=Depends(user_dep)):
    if "System Admin" not in {r.name.value for r in user.roles}: raise HTTPException(403,"Administrator access required")
    return db.scalars(select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(200)).all()

