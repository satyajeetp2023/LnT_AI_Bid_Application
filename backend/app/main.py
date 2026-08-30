import uuid
import logging
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.api.missing_inputs import router as missing_inputs_router
from app.api.pre_bid_queries import router as pre_bid_queries_router
logging.basicConfig(level=logging.INFO,format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}')
settings=get_settings()
app=FastAPI(title="Railway Bid Intelligence API",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.middleware("http")
async def security_headers(request:Request,call_next):
    request_id=request.headers.get("x-request-id") or str(uuid.uuid4())
    response=await call_next(request)
    response.headers["X-Request-ID"]=request_id
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="no-referrer"
    response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"]="no-store"
    if settings.environment.strip().lower()=="production":
        response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response
app.include_router(router,prefix="/api/v1")
app.include_router(missing_inputs_router,prefix="/api/v1")
app.include_router(pre_bid_queries_router,prefix="/api/v1")
