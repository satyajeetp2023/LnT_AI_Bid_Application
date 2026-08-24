import logging
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
logging.basicConfig(level=logging.INFO,format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}')
app=FastAPI(title="Railway Bid Intelligence API",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.middleware("http")
async def security_headers(request:Request,call_next):
    response=await call_next(request); response.headers["X-Content-Type-Options"]="nosniff"; response.headers["X-Frame-Options"]="DENY"; response.headers["Referrer-Policy"]="no-referrer"; return response
app.include_router(router,prefix="/api/v1")

