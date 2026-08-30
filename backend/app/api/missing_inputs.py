from datetime import date
from fastapi import APIRouter,Depends,Header,HTTPException,Query,Request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import BidMissingInput,BidProject,User
from app.schemas.missing_inputs import MissingInputCreate,MissingInputRead,MissingInputUpdate
from app.security.auth import Permission,current_user,require_project_access
from app.services.missing_inputs import create_missing_input,list_missing_inputs,missing_input_summary,update_missing_input
from app.services.estimation_readiness import calculate_estimation_readiness

router=APIRouter()
def user_dep(db:Session=Depends(get_db),x_user_id:int=Header(default=1,alias="X-User-ID")):return current_user(db,x_user_id)
def metadata(request:Request):return {"ip":request.client.host if request.client else None,"user_agent":request.headers.get("user-agent")}
def get_bid(db:Session,bid_id:int):
 bid=db.get(BidProject,bid_id)
 if not bid:raise HTTPException(404,"Bid project not found")
 return bid
def get_item(db:Session,item_id:int):
 item=db.get(BidMissingInput,item_id)
 if not item:raise HTTPException(404,"Missing input not found")
 return item

@router.post("/bids/{bid_id}/missing-inputs",response_model=MissingInputRead,status_code=201)
def add_missing_input(bid_id:int,payload:MissingInputCreate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.MISSING_INPUT_MANAGE);get_bid(db,bid_id);return create_missing_input(db,bid_id,payload,user.id,metadata(request))

@router.get("/bids/{bid_id}/missing-inputs")
def missing_inputs(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep),search:str|None=None,input_category:str|None=None,input_type:str|None=None,priority:str|None=None,status:str|None=None,responsible_function:str|None=None,requirement_id:int|None=None,source_document_id:int|None=None,required_by_from:date|None=None,required_by_to:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
 require_project_access(db,user,bid_id,Permission.MISSING_INPUT_VIEW);get_bid(db,bid_id);rows,total=list_missing_inputs(db,bid_id,locals(),page,page_size);return {"items":[MissingInputRead.model_validate(x).model_dump(mode="json") for x in rows],"total":total,"page":page,"page_size":page_size,"summary":missing_input_summary(db,bid_id)}

@router.get("/bids/{bid_id}/estimation-readiness")
def estimation_readiness(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.MISSING_INPUT_VIEW);get_bid(db,bid_id);return calculate_estimation_readiness(db,bid_id)

@router.get("/missing-inputs/{missing_input_id}",response_model=MissingInputRead)
def missing_input_detail(missing_input_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=get_item(db,missing_input_id);require_project_access(db,user,item.bid_project_id,Permission.MISSING_INPUT_VIEW);return item

@router.patch("/missing-inputs/{missing_input_id}",response_model=MissingInputRead)
def edit_missing_input(missing_input_id:int,payload:MissingInputUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=get_item(db,missing_input_id);require_project_access(db,user,item.bid_project_id,Permission.MISSING_INPUT_MANAGE);return update_missing_input(db,item,payload,user.id,metadata(request))
