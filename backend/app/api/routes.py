from dataclasses import asdict
from datetime import date,timedelta
from fastapi import APIRouter,Depends,File,Header,HTTPException,Query,Request,UploadFile
from fastapi.responses import Response
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.database.session import get_db
from app.models import AuditEvent,BidDocument,BidMissingInput,BidPreBidQuery,BidProject,BidRequirement,ProjectMembership,User
from app.schemas.requirements import RequirementCreate,RequirementExtractionSummary,RequirementRead,RequirementUpdate
from app.schemas.bids import AutoClassifyRequest,BidCreate,BidRead,BidUpdate,ClassificationUpdate,DocumentMetadataUpdate,DocumentRead,NotesUpdate,RevisionCreate
from app.security.auth import Permission,current_user,is_admin,require_permission,require_project_access
from app.services.bids import create_bid,list_bids,update_bid
from app.services.requirements import create_requirement,list_requirements,update_requirement
from app.services.requirement_extraction import extract_requirements_from_document
from app.services.responsibility_assignment import suggest_responsible_function
from app.services.department_workflow import department_work_queue
from app.services.submission_format_intelligence import detect_submission_formats
from app.services.template_structure_parser import parse_xlsx_template
from app.services.template_population_plan import build_population_plan
from app.services.template_draft_generator import generate_controlled_xlsx_draft
from app.services.documents import DOCUMENT_CATEGORIES,archive,classify,mark_revision,update_document_metadata,update_notes,upload_document
from app.services.document_classification import auto_classify_document
from app.storage.base import LocalSecureStorage
router=APIRouter()
def user_dep(db:Session=Depends(get_db),x_user_id:int=Header(default=1,alias="X-User-ID")): return current_user(db,x_user_id)
def metadata(request:Request): return {"ip":request.client.host if request.client else None,"user_agent":request.headers.get("user-agent")}
def get_bid(db,id):
 bid=db.get(BidProject,id)
 if not bid: raise HTTPException(404,"Bid project not found")
 return bid
def get_doc(db,id):
 doc=db.get(BidDocument,id)
 if not doc: raise HTTPException(404,"Document not found")
 return doc
@router.get("/health")
def health(db:Session=Depends(get_db)): db.execute(select(1)); return {"status":"ok","database":"connected"}
@router.get("/config/upload")
def upload_config():
 c=get_settings(); return {"max_file_size_mb":c.max_file_size_mb,"max_batch_size_mb":c.max_batch_size_mb,"max_files_per_batch":c.max_files_per_batch,"allowed_extensions":sorted(c.allowed_extensions),"document_categories":DOCUMENT_CATEGORIES}
@router.get("/auth/me")
def me(user:User=Depends(user_dep)): return {"id":user.id,"name":user.full_name,"roles":[r.name.value for r in user.roles]}
@router.get("/bids",response_model=list[BidRead])
def bids(db:Session=Depends(get_db),user:User=Depends(user_dep)): return list_bids(db,user)
@router.post("/bids",response_model=BidRead,status_code=201)
def add_bid(payload:BidCreate,db:Session=Depends(get_db),user:User=Depends(user_dep)): require_permission(user,Permission.CREATE_BID); return create_bid(db,payload,user.id)
@router.get("/bids/{bid_id}",response_model=BidRead)
def bid_detail(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)): require_project_access(db,user,bid_id,Permission.VIEW_DOCUMENT); return get_bid(db,bid_id)
@router.patch("/bids/{bid_id}",response_model=BidRead)
def edit_bid(bid_id:int,payload:BidUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)): require_project_access(db,user,bid_id,Permission.EDIT_BID); return update_bid(db,get_bid(db,bid_id),payload,user.id,metadata(request))
@router.get("/dashboard/summary")
def dashboard(db:Session=Depends(get_db),user:User=Depends(user_dep)):
 visible=list_bids(db,user); ids=[b.id for b in visible]; today=date.today(); due=today+timedelta(days=30)
 docs=[] if not ids else db.scalars(select(BidDocument).where(BidDocument.bid_project_id.in_(ids),BidDocument.document_status!="Archived")).all()
 return {"active_bids":sum(b.bid_status not in {"Closed","Cancelled","Lost","Won"} for b in visible),"bids_due_soon":sum(today<=b.tender_due_date<=due for b in visible),"documents_uploaded":len(docs),"documents_requiring_review":sum(d.document_status=="Needs Review" for d in docs),"recent_bids":[BidRead.model_validate(b).model_dump(mode="json") for b in visible[:10]]}
@router.post("/bids/{bid_id}/members")
def add_member(bid_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.MANAGE_MEMBERS); target_id=int(payload.get("user_id",0)); role=str(payload.get("role","")).strip()
 if not db.get(User,target_id) or not role: raise HTTPException(422,"Valid user_id and project role are required")
 member=db.scalar(select(ProjectMembership).where(ProjectMembership.bid_project_id==bid_id,ProjectMembership.user_id==target_id))
 if member: member.role=role
 else: member=ProjectMembership(bid_project_id=bid_id,user_id=target_id,role=role);db.add(member)
 db.flush();db.add(AuditEvent(user_id=user.id,bid_project_id=bid_id,event_type="project.membership_changed",entity_type="ProjectMembership",entity_id=str(member.id),request_metadata=metadata(request),details={"member_user_id":target_id,"role":role}));db.commit();return {"id":member.id,"user_id":target_id,"role":role}
@router.get("/bids/{bid_id}/documents")
def documents(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep),search:str|None=None,category:str|None=None,extension:str|None=None,status:str|None=None,uploader:int|None=None,uploaded_date:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
 require_project_access(db,user,bid_id,Permission.VIEW_DOCUMENT); q=select(BidDocument).where(BidDocument.bid_project_id==bid_id)
 if search: q=q.where(BidDocument.original_filename.ilike(f"%{search}%"))
 if category: q=q.where(BidDocument.document_category==category)
 if extension: q=q.where(BidDocument.file_extension==extension)
 if status: q=q.where(BidDocument.document_status==status)
 if uploader: q=q.where(BidDocument.uploaded_by==uploader)
 if uploaded_date: q=q.where(func.date(BidDocument.uploaded_at)==uploaded_date)
 total=db.scalar(select(func.count()).select_from(q.subquery())) or 0; rows=db.scalars(q.order_by(BidDocument.uploaded_at.desc()).offset((page-1)*page_size).limit(page_size)).all()
 return {"items":[DocumentRead.model_validate(x).model_dump(mode="json") for x in rows],"total":total,"page":page,"page_size":page_size}
@router.post("/bids/{bid_id}/documents",response_model=list[DocumentRead])
async def upload(bid_id:int,files:list[UploadFile]=File(...),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.UPLOAD_DOCUMENT); cfg=get_settings()
 if len(files)>cfg.max_files_per_batch: raise HTTPException(413,"Too many files in batch")
 result=[]; total=0
 for file in files:
  data=await file.read(); total+=len(data)
  if total>cfg.max_batch_size_mb*1024*1024: raise HTTPException(413,"Batch exceeds configured size limit")
  result.append(upload_document(db,bid_id,file.filename or "",file.content_type,data,user.id))
 return result
@router.patch("/documents/{document_id}/classification",response_model=DocumentRead)
def reclassify(document_id:int,payload:ClassificationUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); require_project_access(db,user,doc.bid_project_id,Permission.CLASSIFY_DOCUMENT); return classify(db,doc,payload.document_category,payload.document_subcategory,payload.information_tags,user.id,metadata(request))
@router.patch("/documents/{document_id}/metadata",response_model=DocumentRead)
def edit_document_metadata(document_id:int,payload:DocumentMetadataUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); require_project_access(db,user,doc.bid_project_id,Permission.CLASSIFY_DOCUMENT); return update_document_metadata(db,doc,payload,user.id,metadata(request))
@router.post("/documents/{document_id}/auto-classify",response_model=DocumentRead)
def auto_classify(document_id:int,request:Request,payload:AutoClassifyRequest=AutoClassifyRequest(),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); require_project_access(db,user,doc.bid_project_id,Permission.CLASSIFY_DOCUMENT)
 if doc.duplicate_of_document_id or not doc.storage_path: raise HTTPException(422,"Document content is not available for classification")
 if doc.classification_status=="manually_classified" and not payload.force: raise HTTPException(409,"Manual classification is protected; set force=true to replace it")
 return auto_classify_document(db,doc,LocalSecureStorage(get_settings().storage_root),user.id,force=payload.force,request_metadata=metadata(request))
@router.post("/documents/{document_id}/extract-requirements",response_model=RequirementExtractionSummary)
def extract_document_requirements(document_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.REQUIREMENT_MANAGE)
 if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,"Document content is not available for requirement extraction")
 try:return asdict(extract_requirements_from_document(db,doc,LocalSecureStorage(get_settings().storage_root),user.id,metadata(request)))
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
@router.get("/documents/{document_id}/template-structure")
def document_template_structure(document_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.VIEW_DOCUMENT)
 if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,"Document content is not available for template inspection")
 if doc.file_extension.lower()!="xlsx":raise HTTPException(422,"Template structure inspection currently supports .xlsx files only")
 storage=LocalSecureStorage(get_settings().storage_root)
 result=parse_xlsx_template(storage.read(doc.storage_path))
 db.add(AuditEvent(user_id=user.id,bid_project_id=doc.bid_project_id,event_type="template.structure_inspected",entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata(request),details={"parser_version":result.get("parser_version"),"tables_detected":result.get("summary",{}).get("tables_detected",0)}))
 db.commit()
 return result

@router.get("/documents/{document_id}/population-plan")
def document_population_plan(document_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.REQUIREMENT_VIEW)
 if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,"Document content is not available for population planning")
 if doc.file_extension.lower()!="xlsx":raise HTTPException(422,"Population planning currently supports .xlsx templates only")
 storage=LocalSecureStorage(get_settings().storage_root)
 return build_population_plan(db,doc.bid_project_id,storage.read(doc.storage_path))

@router.post("/documents/{document_id}/generate-controlled-draft")
def generate_template_draft(document_id:int,request:Request,payload:dict|None=None,choice_mark:str=Query("X"),include_suggested_text:bool=Query(False),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.REQUIREMENT_MANAGE)
 if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,"Document content is not available for draft generation")
 if doc.file_extension.lower()!="xlsx":raise HTTPException(422,"Controlled draft generation currently supports .xlsx templates only")
 storage=LocalSecureStorage(get_settings().storage_root)
 try:data,summary=generate_controlled_xlsx_draft(db,doc.bid_project_id,storage.read(doc.storage_path),choice_mark,include_suggested_text,(payload or {}).get("header_values") or {})
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
 db.add(AuditEvent(user_id=user.id,bid_project_id=doc.bid_project_id,event_type="template.controlled_draft_generated",entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata(request),details={k:v for k,v in summary.items() if k not in {"written","unresolved"}}))
 db.commit()
 stem=doc.original_filename.rsplit(".",1)[0]
 filename=f"{stem}_controlled_draft.xlsx"
 return Response(data,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="{filename}"',"X-Template-Written-Fields":str(summary["written_fields"]),"X-Template-Unresolved-Fields":str(summary["unresolved_fields"])})

@router.patch("/documents/{document_id}/notes",response_model=DocumentRead)
def notes(document_id:int,payload:NotesUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); require_project_access(db,user,doc.bid_project_id,Permission.CLASSIFY_DOCUMENT); return update_notes(db,doc,payload.notes,user.id,metadata(request))
@router.post("/documents/{document_id}/archive",response_model=DocumentRead)
def archive_doc(document_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); require_project_access(db,user,doc.bid_project_id,Permission.ARCHIVE_DOCUMENT); return archive(db,doc,user.id,metadata(request))
@router.post("/documents/{document_id}/revision",response_model=DocumentRead)
def revision(document_id:int,payload:RevisionCreate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); original=get_doc(db,payload.revision_of_document_id); require_project_access(db,user,doc.bid_project_id,Permission.CLASSIFY_DOCUMENT); return mark_revision(db,doc,original,user.id,metadata(request))
@router.get("/documents/{document_id}/revisions",response_model=list[DocumentRead])
def revisions(document_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); require_project_access(db,user,doc.bid_project_id,Permission.VIEW_DOCUMENT); root=doc.revision_of_document_id or doc.id; return db.scalars(select(BidDocument).where((BidDocument.id==root)|(BidDocument.revision_of_document_id==root)).order_by(BidDocument.revision_no)).all()
@router.get("/documents/{document_id}/download")
def download(document_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id); require_project_access(db,user,doc.bid_project_id,Permission.DOWNLOAD_DOCUMENT)
 if not doc.storage_path: raise HTTPException(404,"Document content not available")
 data=LocalSecureStorage(get_settings().storage_root).read(doc.storage_path); db.add(AuditEvent(user_id=user.id,bid_project_id=doc.bid_project_id,event_type="document.downloaded",entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata(request))); db.commit(); safe=doc.original_filename.replace('"',''); return Response(data,media_type=doc.mime_type,headers={"Content-Disposition":f'attachment; filename="{safe}"'})
@router.get("/bids/{bid_id}/members")
def project_members(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.VIEW_DOCUMENT);get_bid(db,bid_id)
 memberships=db.scalars(select(ProjectMembership).where(ProjectMembership.bid_project_id==bid_id).order_by(ProjectMembership.role)).all()
 result=[]
 for membership in memberships:
  member=db.get(User,membership.user_id)
  if member and member.is_active:
   result.append({"user_id":member.id,"name":member.full_name,"email":member.email,"project_role":membership.role})
 return result

@router.post("/bids/{bid_id}/work-items/assign-person")
def assign_work_item_person(bid_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 get_bid(db,bid_id)
 entity_type=str(payload.get("entity_type","")).strip()
 entity_id=int(payload.get("entity_id",0))
 target_user_id=payload.get("user_id")
 model=None;permission=None
 if entity_type=="Requirement":model=BidRequirement;permission=Permission.REQUIREMENT_MANAGE
 elif entity_type=="Missing Input":model=BidMissingInput;permission=Permission.MISSING_INPUT_MANAGE
 elif entity_type=="Pre-Bid Query":model=BidPreBidQuery;permission=Permission.PRE_BID_QUERY_MANAGE
 else:raise HTTPException(422,"Unsupported work item type")
 require_project_access(db,user,bid_id,permission)
 item=db.get(model,entity_id)
 if not item or item.bid_project_id!=bid_id:raise HTTPException(404,"Work item not found in this bid")
 person_name=None
 if target_user_id is not None:
  target_user_id=int(target_user_id)
  membership=db.scalar(select(ProjectMembership).where(ProjectMembership.bid_project_id==bid_id,ProjectMembership.user_id==target_user_id))
  target=db.get(User,target_user_id)
  if not membership or not target or not target.is_active:raise HTTPException(422,"Responsible person must be an active member of this bid")
  person_name=target.full_name
 item.responsible_person=person_name
 db.add(AuditEvent(user_id=user.id,bid_project_id=bid_id,event_type="work_item.person_assigned",entity_type=entity_type,entity_id=str(entity_id),request_metadata=metadata(request),details={"responsible_person":person_name,"responsible_user_id":target_user_id}))
 db.commit()
 return {"entity_type":entity_type,"entity_id":entity_id,"responsible_person":person_name}

@router.get("/bids/{bid_id}/submission-format-candidates")
def submission_format_candidates(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW);get_bid(db,bid_id);return detect_submission_formats(db,bid_id)

@router.get("/bids/{bid_id}/department-work-queue")
def get_department_work_queue(bid_id:int,responsible_function:str|None=None,mine:bool=False,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW);get_bid(db,bid_id);return department_work_queue(db,bid_id,responsible_function,user.full_name if mine else None)

@router.post("/bids/{bid_id}/auto-assign-owners")
def auto_assign_owners(bid_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_MANAGE);get_bid(db,bid_id)
 counts={"requirements":0,"missing_inputs":0,"pre_bid_queries":0}
 requirements=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==bid_id)).all()
 for item in requirements:
  if item.responsible_function:continue
  item.responsible_function=suggest_responsible_function(item.requirement_category,item.requirement_text);counts["requirements"]+=1
 missing_inputs=db.scalars(select(BidMissingInput).where(BidMissingInput.bid_project_id==bid_id)).all()
 for item in missing_inputs:
  if item.responsible_function:continue
  if item.requirement and item.requirement.responsible_function:item.responsible_function=item.requirement.responsible_function
  else:item.responsible_function=suggest_responsible_function(item.input_category,item.missing_input_description)
  counts["missing_inputs"]+=1
 pre_bid_queries=db.scalars(select(BidPreBidQuery).where(BidPreBidQuery.bid_project_id==bid_id)).all()
 for item in pre_bid_queries:
  if item.responsible_function:continue
  if item.requirement and item.requirement.responsible_function:item.responsible_function=item.requirement.responsible_function
  elif item.missing_input and item.missing_input.responsible_function:item.responsible_function=item.missing_input.responsible_function
  else:item.responsible_function=suggest_responsible_function(item.query_category,item.query_text)
  counts["pre_bid_queries"]+=1
 db.add(AuditEvent(user_id=user.id,bid_project_id=bid_id,event_type="bid.responsibility_auto_assigned",entity_type="BidProject",entity_id=str(bid_id),request_metadata=metadata(request),details=counts))
 db.commit()
 return counts

@router.post("/bids/{bid_id}/requirements",response_model=RequirementRead,status_code=201)
def add_requirement(bid_id:int,payload:RequirementCreate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_MANAGE);get_bid(db,bid_id);return create_requirement(db,bid_id,payload,user.id,metadata(request))
@router.get("/bids/{bid_id}/requirements")
def requirements(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep),search:str|None=None,category:str|None=None,requirement_type:str|None=None,priority:str|None=None,requirement_status:str|None=None,compliance_status:str|None=None,responsible_function:str|None=None,source_document_id:int|None=None,due_date:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW);rows,total=list_requirements(db,bid_id,locals(),page,page_size);base=BidRequirement.bid_project_id==bid_id
 count=lambda condition:db.scalar(select(func.count()).select_from(BidRequirement).where(base,condition)) or 0
 summary={"total":count(BidRequirement.id>0),"critical":count(BidRequirement.priority=="Critical"),"open":count(BidRequirement.requirement_status=="Open"),"needs_review":count(BidRequirement.review_status.in_(("Not Reviewed","Needs Clarification"))),"non_compliant":count(BidRequirement.compliance_status=="Non-Compliant")}
 return {"items":[RequirementRead.model_validate(x).model_dump(mode="json") for x in rows],"total":total,"page":page,"page_size":page_size,"summary":summary}
@router.get("/requirements/{requirement_id}",response_model=RequirementRead)
def requirement_detail(requirement_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=db.get(BidRequirement,requirement_id)
 if not item:raise HTTPException(404,"Requirement not found")
 require_project_access(db,user,item.bid_project_id,Permission.REQUIREMENT_VIEW);return item
@router.patch("/requirements/{requirement_id}",response_model=RequirementRead)
def edit_requirement(requirement_id:int,payload:RequirementUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=db.get(BidRequirement,requirement_id)
 if not item:raise HTTPException(404,"Requirement not found")
 require_project_access(db,user,item.bid_project_id,Permission.REQUIREMENT_MANAGE);return update_requirement(db,item,payload,user.id,metadata(request))
@router.get("/audit")
def audit(db:Session=Depends(get_db),user:User=Depends(user_dep),page:int=1,page_size:int=50):
 require_permission(user,Permission.VIEW_AUDIT); rows=db.scalars(select(AuditEvent).order_by(AuditEvent.timestamp.desc()).offset((page-1)*page_size).limit(min(page_size,100))).all(); return [{"id":x.id,"timestamp":x.timestamp,"user":x.user.full_name if x.user else None,"event_type":x.event_type,"entity_type":x.entity_type,"entity_id":x.entity_id,"bid_project_id":x.bid_project_id,"request_metadata":x.request_metadata,"details":x.details} for x in rows]
