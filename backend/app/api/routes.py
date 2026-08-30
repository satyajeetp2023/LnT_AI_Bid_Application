from dataclasses import asdict
from datetime import date,timedelta
from decimal import Decimal
from fastapi import APIRouter,Depends,File,Header,HTTPException,Query,Request,UploadFile
from fastapi.responses import Response
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.database.session import get_db
from app.models import AuditEvent,BidClauseRiskFinding,BidDocument,BidMissingInput,BidPreBidQuery,BidPreparedArtifact,BidProject,BidRequirement,ProductivityBenchmark,ProjectMembership,ScheduleScopeItem,User
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
from app.services.prepared_artifacts import approve_artifact,artifact_dict,create_prepared_artifact,get_prepared_artifact,list_prepared_artifacts,mark_artifact_ready
from app.services.submission_readiness import build_submission_package,submission_readiness
from app.services.p6_xer import analyze_schedule_tables
from app.services.schedule_requirement_alignment import align_schedule_to_requirements
from app.services.p6_schedule_comparison import compare_schedule_tables
from app.services.p6_schedule_optimizer import activity_parameter_profile_from_tables,build_schedule_optimization_from_tables
from app.services.schedule_scope_coverage import add_scope_item,disposition_scope_item,evaluate_scope_coverage_from_tables,schedule_scope_catalog,sync_scope_from_requirements
from app.services.boq_scope_adapter import ingest_boq_scope
from app.services.boq_document_extraction import extract_boq_rows
from app.services.schedule_skeleton import build_schedule_skeleton
from app.services.productivity_benchmarks import activity_key,benchmark_summary
from app.services.clause_risk_intelligence import bid_clause_risk_summary,firm_risk_library,promote_finding_to_firm_pattern,review_clause_risk,scan_document_clause_risks
from app.services.tender_qa import tender_question_answer
from app.services.schedule_ingestion import SCHEDULE_EXTENSIONS,ingest_schedule
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
 try:data,summary=generate_controlled_xlsx_draft(db,doc.bid_project_id,storage.read(doc.storage_path),choice_mark,include_suggested_text,(payload or {}).get("header_values") or {},(payload or {}).get("field_overrides") or {})
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
 db.add(AuditEvent(user_id=user.id,bid_project_id=doc.bid_project_id,event_type="template.controlled_draft_generated",entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata(request),details={k:v for k,v in summary.items() if k not in {"written","unresolved"}}))
 db.commit()
 stem=doc.original_filename.rsplit(".",1)[0]
 filename=f"{stem}_controlled_draft.xlsx"
 return Response(data,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="{filename}"',"X-Template-Written-Fields":str(summary["written_fields"]),"X-Template-Unresolved-Fields":str(summary["unresolved_fields"])})

@router.post("/documents/{document_id}/save-controlled-draft")
def save_template_draft(document_id:int,request:Request,payload:dict|None=None,choice_mark:str=Query("X"),include_suggested_text:bool=Query(False),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.PREPARED_ARTIFACT_MANAGE)
 if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,"Document content is not available for prepared artifact generation")
 if doc.file_extension.lower()!="xlsx":raise HTTPException(422,"Prepared artifact generation currently supports .xlsx templates only")
 storage=LocalSecureStorage(get_settings().storage_root)
 try:data,summary=generate_controlled_xlsx_draft(db,doc.bid_project_id,storage.read(doc.storage_path),choice_mark,include_suggested_text,(payload or {}).get("header_values") or {},(payload or {}).get("field_overrides") or {})
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
 item=create_prepared_artifact(db,doc,data,summary,storage,user.id,metadata(request))
 return artifact_dict(item)

@router.get("/bids/{bid_id}/submission-readiness")
def get_submission_readiness(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.PREPARED_ARTIFACT_VIEW);get_bid(db,bid_id)
 return submission_readiness(db,bid_id)

@router.post("/bids/{bid_id}/submission-package")
def generate_submission_package(bid_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.PREPARED_ARTIFACT_MANAGE);bid=get_bid(db,bid_id)
 storage=LocalSecureStorage(get_settings().storage_root)
 try:data,summary=build_submission_package(db,bid_id,storage)
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
 db.add(AuditEvent(user_id=user.id,bid_project_id=bid_id,event_type="submission.package_generated",entity_type="BidProject",entity_id=str(bid_id),request_metadata=metadata(request),details=summary))
 db.commit()
 safe=bid.bid_id.replace('"','')
 return Response(data,media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="{safe}_submission_package.zip"'})

@router.get("/bids/{bid_id}/prepared-artifacts")
def prepared_artifacts(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.PREPARED_ARTIFACT_VIEW);get_bid(db,bid_id)
 return [artifact_dict(x) for x in list_prepared_artifacts(db,bid_id)]

@router.get("/prepared-artifacts/{artifact_id}/download")
def download_prepared_artifact(artifact_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=get_prepared_artifact(db,artifact_id);require_project_access(db,user,item.bid_project_id,Permission.PREPARED_ARTIFACT_VIEW)
 data=LocalSecureStorage(get_settings().storage_root).read(item.storage_path)
 safe=item.artifact_name.replace('"','')
 return Response(data,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="{safe}.xlsx"'})

@router.post("/prepared-artifacts/{artifact_id}/ready-for-review")
def prepared_artifact_ready(artifact_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=get_prepared_artifact(db,artifact_id);require_project_access(db,user,item.bid_project_id,Permission.PREPARED_ARTIFACT_MANAGE)
 return artifact_dict(mark_artifact_ready(db,item,user.id,metadata(request)))

@router.post("/prepared-artifacts/{artifact_id}/approve")
def approve_prepared_artifact(artifact_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=get_prepared_artifact(db,artifact_id);require_project_access(db,user,item.bid_project_id,Permission.PREPARED_ARTIFACT_APPROVE)
 return artifact_dict(approve_artifact(db,item,user.id,metadata(request)))

@router.get("/documents/{document_id}/schedule-analysis")
def schedule_analysis(document_id:int,request:Request,long_duration_hours:float=Query(160,gt=0,le=10000),near_critical_hours:float=Query(40,ge=0,le=10000),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.VIEW_DOCUMENT)
 if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,"Document content is not available for schedule analysis")
 if doc.file_extension.lower() not in SCHEDULE_EXTENSIONS:raise HTTPException(422,"This file type is not supported for schedule ingestion")
 content=LocalSecureStorage(get_settings().storage_root).read(doc.storage_path)
 ingestion=ingest_schedule(doc.file_extension,content)
 if not ingestion["detected"]:raise HTTPException(422,"No reliable structured schedule activity table could be extracted from this document")
 result=analyze_schedule_tables(ingestion["tables"],long_duration_hours,near_critical_hours,ingestion["capabilities"])
 result["optimization_advisor"]=build_schedule_optimization_from_tables(ingestion["tables"],near_critical_hours,long_duration_hours,ingestion["capabilities"])
 result["tender_alignment"]=align_schedule_to_requirements(db,doc.bid_project_id,result)
 result["source_ingestion"]={k:ingestion[k] for k in ("source_kind","fidelity","capabilities","limitations","parser_version")}
 db.add(AuditEvent(user_id=user.id,bid_project_id=doc.bid_project_id,event_type="schedule.analyzed",entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata(request),details={"source_kind":ingestion["source_kind"],"fidelity":ingestion["fidelity"],"activities":result.get("counts",{}).get("activities",0),"health_score":result.get("health",{}).get("score"),"alignment_grade":result.get("tender_alignment",{}).get("grade")}))
 db.commit()
 return result

@router.get("/documents/{document_id}/schedule-comparison")
def schedule_comparison(document_id:int,request:Request,baseline_document_id:int=Query(...,ge=1),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 current=get_doc(db,document_id);baseline=get_doc(db,baseline_document_id)
 require_project_access(db,user,current.bid_project_id,Permission.VIEW_DOCUMENT)
 if current.bid_project_id!=baseline.bid_project_id:raise HTTPException(422,"Baseline and current schedule must belong to the same bid")
 for doc,label in ((baseline,"Baseline"),(current,"Current")):
  if doc.file_extension.lower() not in SCHEDULE_EXTENSIONS:raise HTTPException(422,f"{label} file type is not supported for schedule comparison")
  if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,f"{label} schedule content is not available")
 if current.id==baseline.id:raise HTTPException(422,"Baseline and current schedule must be different documents")
 storage=LocalSecureStorage(get_settings().storage_root)
 base_ing=ingest_schedule(baseline.file_extension,storage.read(baseline.storage_path))
 cur_ing=ingest_schedule(current.file_extension,storage.read(current.storage_path))
 if not base_ing["detected"] or not cur_ing["detected"]:raise HTTPException(422,"Both documents must contain a reliable structured activity table")
 result=compare_schedule_tables(base_ing["tables"],cur_ing["tables"],base_ing["capabilities"],cur_ing["capabilities"])
 result["source_fidelity"]={"baseline":base_ing["fidelity"],"current":cur_ing["fidelity"]}
 db.add(AuditEvent(user_id=user.id,bid_project_id=current.bid_project_id,event_type="schedule.compared",entity_type="BidDocument",entity_id=str(current.id),request_metadata=metadata(request),details={"baseline_document_id":baseline.id,"current_document_id":current.id,"baseline_format":baseline.file_extension,"current_format":current.file_extension,**result.get("summary",{})}))
 db.commit()
 return result

@router.get("/documents/{document_id}/schedule-activity-profile")
def schedule_activity_profile(document_id:int,task_key:str=Query(...,min_length=1,max_length=200),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.VIEW_DOCUMENT)
 if not doc.storage_path or doc.file_extension.lower() not in SCHEDULE_EXTENSIONS:raise HTTPException(422,"Supported schedule content is required")
 ingestion=ingest_schedule(doc.file_extension,LocalSecureStorage(get_settings().storage_root).read(doc.storage_path))
 if not ingestion["detected"]:raise HTTPException(422,"No reliable structured activity table could be extracted")
 profile=activity_parameter_profile_from_tables(ingestion["tables"],task_key)
 if not profile:raise HTTPException(404,"Activity not found in this schedule")
 profile["source_ingestion"]={k:ingestion[k] for k in ("source_kind","fidelity","capabilities","limitations")}
 return profile

@router.post("/bids/{bid_id}/schedule-scope/sync")
def sync_schedule_scope(bid_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_MANAGE);get_bid(db,bid_id)
 return sync_scope_from_requirements(db,bid_id,user.id,metadata(request))

@router.get("/documents/{document_id}/schedule-source-profile")
def schedule_source_profile(document_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.VIEW_DOCUMENT)
 ext=doc.file_extension.lower()
 if ext not in SCHEDULE_EXTENSIONS:
  return {"recognized":False,"structured":False,"source_kind":f"{ext.upper()} Document","fidelity":"Unsupported","capabilities":{"activities":False,"logic":False,"float":False,"resources":False,"calendars":False,"wbs":False},"limitations":["This file type is not currently recognized as a schedule source."]}
 if not doc.storage_path:
  return {"recognized":True,"structured":False,"source_kind":f"{ext.upper()} Schedule","fidelity":"Content Unavailable","capabilities":{"activities":False,"logic":False,"float":False,"resources":False,"calendars":False,"wbs":False},"limitations":["Document content is not available in storage."]}
 ingestion=ingest_schedule(ext,LocalSecureStorage(get_settings().storage_root).read(doc.storage_path))
 filename=(doc.original_filename or "").lower()
 filename_signal=any(x in filename for x in ("schedule","programme","program","primavera","baseline","work plan","time schedule"))
 return {
  "recognized":bool(ingestion["detected"] or filename_signal or ext in {"xer","mpp"} or (doc.document_type or "").lower().startswith("schedule -")),
  "structured":bool(ingestion["detected"]),
  "source_kind":ingestion["source_kind"],
  "fidelity":ingestion["fidelity"],
  "capabilities":ingestion["capabilities"],
  "limitations":ingestion["limitations"],
  "parser_version":ingestion["parser_version"],
 }

@router.post("/documents/{document_id}/detect-schedule")
def detect_schedule_document(document_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.CLASSIFY_DOCUMENT)
 if doc.duplicate_of_document_id or not doc.storage_path:
  return {"detected":False,"reason":"Document content is not available"}
 ext=doc.file_extension.lower()
 if ext not in SCHEDULE_EXTENSIONS:
  return {"detected":False,"reason":"File type is not supported for schedule ingestion"}
 content=LocalSecureStorage(get_settings().storage_root).read(doc.storage_path)
 ingestion=ingest_schedule(ext,content)
 filename=(doc.original_filename or "").lower()
 filename_signal=any(x in filename for x in ("schedule","programme","program","primavera","baseline","work plan","time schedule"))
 intrinsic_schedule=ext in {"xer","mpp"}
 detected=bool(ingestion["detected"] or filename_signal or intrinsic_schedule)
 if detected and doc.classification_status!="manually_classified":
  doc.document_category="Forms / Formats / Schedules"
  doc.document_type=f"Schedule - {ingestion['source_kind']}"
  doc.classification_confidence=Decimal(str(.98 if ingestion["detected"] else .62))
  doc.classification_status="classified" if ingestion["detected"] else "needs_review"
 db.add(AuditEvent(user_id=user.id,bid_project_id=doc.bid_project_id,event_type="schedule.document_detected",entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata(request),details={"detected":detected,"structured":bool(ingestion["detected"]),"source_kind":ingestion["source_kind"],"fidelity":ingestion["fidelity"],"capabilities":ingestion["capabilities"]}))
 db.commit()
 return {"detected":detected,"structured":bool(ingestion["detected"]),"source_kind":ingestion["source_kind"],"fidelity":ingestion["fidelity"],"capabilities":ingestion["capabilities"],"limitations":ingestion["limitations"]}

@router.get("/bids/{bid_id}/schedule-documents")
def schedule_documents(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.VIEW_DOCUMENT);get_bid(db,bid_id)
 rows=db.scalars(select(BidDocument).where(
  BidDocument.bid_project_id==bid_id,
  BidDocument.document_status!="Archived",
 ).order_by(BidDocument.uploaded_at.desc())).all()
 result=[]
 for doc in rows:
  dtype=(doc.document_type or "").lower()
  name=(doc.original_filename or "").lower()
  candidate=(
   dtype.startswith("schedule -")
   or doc.file_extension.lower() in {"xer","mpp"}
   or any(x in name for x in ("schedule","programme","program","primavera","baseline","time schedule"))
  )
  if not candidate:continue
  result.append(DocumentRead.model_validate(doc).model_dump(mode="json"))
 return result

@router.post("/documents/{document_id}/extract-boq-scope")
def extract_document_boq_scope(document_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.REQUIREMENT_MANAGE)
 if doc.duplicate_of_document_id or not doc.storage_path:raise HTTPException(422,"Document content is not available for BOQ extraction")
 if doc.file_extension.lower() not in {"xlsx","csv"}:
  return {"detected":False,"rows":0,"tables":0,"ingested":{"created":0,"updated":0,"skipped":0}}
 storage=LocalSecureStorage(get_settings().storage_root)
 extracted=extract_boq_rows(doc.file_extension,storage.read(doc.storage_path))
 ingested={"rows_received":0,"created":0,"updated":0,"skipped":0}
 if extracted.get("detected"):
  ingested=ingest_boq_scope(db,doc.bid_project_id,extracted.get("rows") or [],user.id,metadata(request))
 db.add(AuditEvent(user_id=user.id,bid_project_id=doc.bid_project_id,event_type="schedule.boq_document_checked",entity_type="BidDocument",entity_id=str(doc.id),request_metadata=metadata(request),details={"detected":bool(extracted.get("detected")),"rows":len(extracted.get("rows") or []),"tables":len(extracted.get("tables") or [])}))
 db.commit()
 return {"detected":bool(extracted.get("detected")),"rows":len(extracted.get("rows") or []),"tables":len(extracted.get("tables") or []),"ingested":ingested,"extractor_version":extracted.get("version")}

@router.post("/bids/{bid_id}/schedule-scope/boq")
def ingest_schedule_boq_scope(bid_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_MANAGE);get_bid(db,bid_id)
 rows=payload.get("rows") or []
 if not isinstance(rows,list):raise HTTPException(422,"rows must be a list of BOQ items")
 return ingest_boq_scope(db,bid_id,rows,user.id,metadata(request))

@router.get("/bids/{bid_id}/productivity-benchmark")
def get_productivity_benchmark(bid_id:int,activity_name:str=Query(...,min_length=1,max_length=300),unit:str=Query(...,min_length=1,max_length=50),discipline:str|None=Query(None,max_length=100),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW)
 bid=get_bid(db,bid_id)
 return benchmark_summary(db,activity_name,unit,bid.project_type,discipline)

@router.post("/bids/{bid_id}/productivity-benchmarks")
def add_productivity_benchmark(bid_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_MANAGE)
 bid=get_bid(db,bid_id)
 activity_name=str(payload.get("activity_name") or "").strip()
 unit=str(payload.get("unit") or "").strip()
 try:rate=Decimal(str(payload.get("rate_per_working_day")))
 except Exception:raise HTTPException(422,"A valid rate_per_working_day is required") from None
 if not activity_name or not unit or rate<=0:raise HTTPException(422,"activity_name, unit and a positive rate are required")
 confidence=Decimal(str(payload.get("confidence") or "0.60"))
 if confidence<0 or confidence>1:raise HTTPException(422,"confidence must be between 0 and 1")
 row=ProductivityBenchmark(
  activity_name=activity_name,
  activity_key=activity_key(activity_name),
  project_type=str(payload.get("project_type") or bid.project_type or "").strip() or None,
  discipline=str(payload.get("discipline") or "").strip() or None,
  unit=unit,
  rate_per_working_day=rate,
  resource_context=str(payload.get("resource_context") or "").strip() or None,
  source_type="User Confirmed",
  source_reference=str(payload.get("source_reference") or "").strip() or None,
  bid_project_id=bid_id,
  confidence=confidence,
  notes=str(payload.get("notes") or "").strip() or None,
  created_by=user.id,
 )
 db.add(row);db.flush()
 db.add(AuditEvent(user_id=user.id,bid_project_id=bid_id,event_type="schedule.productivity_benchmark_added",entity_type="ProductivityBenchmark",entity_id=str(row.id),request_metadata=metadata(request),details={"activity_name":activity_name,"unit":unit,"rate_per_working_day":str(rate),"source_type":"User Confirmed"}))
 db.commit();db.refresh(row)
 return {"id":row.id,"activity_name":row.activity_name,"unit":row.unit,"rate_per_working_day":float(row.rate_per_working_day),"confidence":float(row.confidence),"source_type":row.source_type}

@router.post("/bids/{bid_id}/tender-qa")
def ask_tender(bid_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW);get_bid(db,bid_id)
 question=str(payload.get("question") or "").strip()
 if not question:raise HTTPException(422,"question is required")
 result=tender_question_answer(db,bid_id,question,LocalSecureStorage(get_settings().storage_root),user.id,metadata(request))
 db.add(AuditEvent(user_id=user.id,bid_project_id=bid_id,event_type="tender_qa.asked",entity_type="BidProject",entity_id=str(bid_id),request_metadata=metadata(request),details={"question":question[:500],"grounded":result["grounded"],"confidence":result["confidence"],"evidence_count":len(result["evidence"])}))
 db.commit()
 return result

@router.post("/documents/{document_id}/scan-clause-risks")
def scan_clause_risks(document_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.REQUIREMENT_MANAGE)
 if doc.file_extension.lower() not in {"pdf","docx","txt"}:
  return {"document_id":doc.id,"created":0,"patterns_checked":0,"supported":False,"reason":"Clause-risk text scan currently supports PDF, DOCX and TXT."}
 try:
  result=scan_document_clause_risks(db,doc,LocalSecureStorage(get_settings().storage_root),user.id,metadata(request))
  result["supported"]=True
  return result
 except ValueError as exc:raise HTTPException(422,str(exc)) from None

@router.get("/bids/{bid_id}/clause-risks")
def get_clause_risks(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW);get_bid(db,bid_id)
 return bid_clause_risk_summary(db,bid_id)

@router.post("/clause-risks/{finding_id}/review")
def review_clause_risk_finding(finding_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 finding=db.get(BidClauseRiskFinding,finding_id)
 if not finding:raise HTTPException(404,"Clause-risk finding not found")
 require_project_access(db,user,finding.bid_project_id,Permission.REQUIREMENT_MANAGE)
 try:
  result=review_clause_risk(db,finding_id,str(payload.get("disposition") or ""),payload.get("comment"),user.id)
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
 db.add(AuditEvent(user_id=user.id,bid_project_id=finding.bid_project_id,event_type="clause_risk.reviewed",entity_type="BidClauseRiskFinding",entity_id=str(finding_id),request_metadata=metadata(request),details={"disposition":result["reviewer_disposition"]}))
 db.commit()
 return result

@router.get("/firm-risk-library")
def get_firm_risk_library(db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_permission(user,Permission.REQUIREMENT_VIEW)
 return firm_risk_library(db)

@router.post("/clause-risks/{finding_id}/promote-pattern")
def promote_clause_risk_pattern(finding_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 finding=db.get(BidClauseRiskFinding,finding_id)
 if not finding:raise HTTPException(404,"Clause-risk finding not found")
 require_project_access(db,user,finding.bid_project_id,Permission.REQUIREMENT_MANAGE)
 try:return promote_finding_to_firm_pattern(db,finding_id,payload,user.id)
 except ValueError as exc:raise HTTPException(422,str(exc)) from None

@router.get("/bids/{bid_id}/schedule-skeleton")
def get_schedule_skeleton(bid_id:int,request:Request,sync_scope:bool=Query(True),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW);get_bid(db,bid_id)
 if sync_scope:sync_scope_from_requirements(db,bid_id,user.id,metadata(request))
 return build_schedule_skeleton(db,bid_id)

@router.get("/bids/{bid_id}/schedule-scope/catalog")
def get_schedule_scope_catalog(bid_id:int,request:Request,sync:bool=Query(True),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_VIEW);get_bid(db,bid_id)
 if sync:sync_scope_from_requirements(db,bid_id,user.id,metadata(request))
 return schedule_scope_catalog(db,bid_id)

@router.post("/bids/{bid_id}/schedule-scope/items")
def create_schedule_scope_item(bid_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.REQUIREMENT_MANAGE);get_bid(db,bid_id)
 try:return add_scope_item(db,bid_id,payload,user.id,metadata(request))
 except ValueError as exc:raise HTTPException(422,str(exc)) from None

@router.get("/documents/{document_id}/schedule-scope-coverage")
def schedule_scope_coverage(document_id:int,request:Request,sync_requirements:bool=Query(True),db:Session=Depends(get_db),user:User=Depends(user_dep)):
 doc=get_doc(db,document_id);require_project_access(db,user,doc.bid_project_id,Permission.REQUIREMENT_VIEW)
 if not doc.storage_path or doc.file_extension.lower() not in SCHEDULE_EXTENSIONS:raise HTTPException(422,"Supported schedule content is required")
 ingestion=ingest_schedule(doc.file_extension,LocalSecureStorage(get_settings().storage_root).read(doc.storage_path))
 if not ingestion["detected"]:raise HTTPException(422,"No reliable structured activity table could be extracted for scope coverage")
 if sync_requirements:sync_scope_from_requirements(db,doc.bid_project_id,user.id,metadata(request))
 result=evaluate_scope_coverage_from_tables(db,doc.bid_project_id,ingestion["tables"],user.id,metadata(request),ingestion["capabilities"])
 result["source_ingestion"]={k:ingestion[k] for k in ("source_kind","fidelity","capabilities","limitations")}
 return result

@router.post("/schedule-scope/items/{item_id}/disposition")
def schedule_scope_disposition(item_id:int,payload:dict,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=db.get(ScheduleScopeItem,item_id)
 if not item:raise HTTPException(404,"Schedule scope item not found")
 require_project_access(db,user,item.bid_project_id,Permission.REQUIREMENT_MANAGE)
 try:return disposition_scope_item(db,item_id,str(payload.get("status") or ""),payload.get("reason"),user.id,metadata(request))
 except ValueError as exc:raise HTTPException(422,str(exc)) from None

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
 elif entity_type=="Schedule Scope":model=ScheduleScopeItem;permission=Permission.REQUIREMENT_MANAGE
 elif entity_type=="Clause Risk":model=BidClauseRiskFinding;permission=Permission.REQUIREMENT_MANAGE
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
