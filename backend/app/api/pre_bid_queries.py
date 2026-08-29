from datetime import date
from fastapi import APIRouter,Depends,Header,HTTPException,Query,Request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import BidPreBidQuery,BidProject,User
from app.schemas.pre_bid_queries import PreBidQueryCreate,PreBidQueryRead,PreBidQueryUpdate
from app.security.auth import Permission,current_user,require_project_access
from app.services.pre_bid_queries import create_pre_bid_query,list_pre_bid_queries,pre_bid_query_summary,update_pre_bid_query
from app.services.pre_bid_query_intelligence import suggest_pre_bid_queries

router=APIRouter()
def user_dep(db:Session=Depends(get_db),x_user_id:int=Header(default=1,alias="X-User-ID")):return current_user(db,x_user_id)
def metadata(request:Request):return {"ip":request.client.host if request.client else None,"user_agent":request.headers.get("user-agent")}
def get_bid(db:Session,bid_id:int):
 bid=db.get(BidProject,bid_id)
 if not bid:raise HTTPException(404,"Bid project not found")
 return bid
def get_item(db:Session,item_id:int):
 item=db.get(BidPreBidQuery,item_id)
 if not item:raise HTTPException(404,"Pre-bid query not found")
 return item

@router.post("/bids/{bid_id}/pre-bid-queries",response_model=PreBidQueryRead,status_code=201)
def add_pre_bid_query(bid_id:int,payload:PreBidQueryCreate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.PRE_BID_QUERY_MANAGE);get_bid(db,bid_id);return create_pre_bid_query(db,bid_id,payload,user.id,metadata(request))

@router.get("/bids/{bid_id}/pre-bid-queries")
def pre_bid_queries(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep),search:str|None=None,query_category:str|None=None,priority:str|None=None,status:str|None=None,responsible_function:str|None=None,requirement_id:int|None=None,missing_input_id:int|None=None,source_document_id:int|None=None,target_response_from:date|None=None,target_response_to:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
 require_project_access(db,user,bid_id,Permission.PRE_BID_QUERY_VIEW);get_bid(db,bid_id);rows,total=list_pre_bid_queries(db,bid_id,locals(),page,page_size);return {"items":[PreBidQueryRead.model_validate(x).model_dump(mode="json") for x in rows],"total":total,"page":page,"page_size":page_size,"summary":pre_bid_query_summary(db,bid_id)}

@router.get("/bids/{bid_id}/pre-bid-query-suggestions")
def pre_bid_query_suggestions(bid_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 require_project_access(db,user,bid_id,Permission.PRE_BID_QUERY_VIEW);get_bid(db,bid_id);return suggest_pre_bid_queries(db,bid_id)

@router.get("/pre-bid-queries/{query_id}",response_model=PreBidQueryRead)
def pre_bid_query_detail(query_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=get_item(db,query_id);require_project_access(db,user,item.bid_project_id,Permission.PRE_BID_QUERY_VIEW);return item

@router.patch("/pre-bid-queries/{query_id}",response_model=PreBidQueryRead)
def edit_pre_bid_query(query_id:int,payload:PreBidQueryUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(user_dep)):
 item=get_item(db,query_id);require_project_access(db,user,item.bid_project_id,Permission.PRE_BID_QUERY_MANAGE);return update_pre_bid_query(db,item,payload,user.id,metadata(request))
