import {authMode,beginLogin,getAccessToken} from "@/services/auth";

export const API=process.env.NEXT_PUBLIC_API_URL||"http://127.0.0.1:8000/api/v1";
export const DEFAULT_REQUEST_TIMEOUT_MS=30000;

export type ApiRequestInit=RequestInit&{timeoutMs?:number};

function timeoutMessage(timeoutMs:number){
 const seconds=Math.max(1,Math.round(timeoutMs/1000));
 return `The service did not respond within ${seconds} seconds. Please try again.`;
}

export async function request<T>(path:string,init:ApiRequestInit={}):Promise<T>{
 const mode=authMode();
 const headers=new Headers(init.headers||{});
 if(!(init.body instanceof FormData)&&!headers.has("Content-Type"))headers.set("Content-Type","application/json");
 if(mode==="development_header"){
  headers.set("X-User-ID","1");
 }else if(mode==="oidc"){
  const token=getAccessToken();
  if(!token){
   if(typeof window!=="undefined")await beginLogin(window.location.pathname+window.location.search);
   throw new Error("Enterprise authentication is required");
  }
  headers.set("Authorization","Bearer "+token);
 }else{
  throw new Error("Unsupported frontend authentication mode");
 }

 const timeoutMs=Math.max(1,init.timeoutMs??DEFAULT_REQUEST_TIMEOUT_MS);
 const controller=new AbortController();
 let timedOut=false;
 const timeoutId=setTimeout(()=>{timedOut=true;controller.abort()},timeoutMs);
 const externalSignal=init.signal;
 const abortFromCaller=()=>controller.abort();
 if(externalSignal){
  if(externalSignal.aborted)controller.abort();
  else externalSignal.addEventListener("abort",abortFromCaller,{once:true});
 }

 const {timeoutMs:_timeoutMs,signal:_signal,...fetchInit}=init;
 try{
  const r=await fetch(API+path,{...fetchInit,headers,signal:controller.signal});
  if(r.status===401&&mode==="oidc"&&typeof window!=="undefined"){
   await beginLogin(window.location.pathname+window.location.search);
   throw new Error("Enterprise session expired");
  }
  if(!r.ok){
   const e=await r.json().catch(()=>({detail:"Request failed"}));
   throw new Error(e.detail||"Request failed");
  }
  return r.json();
 }catch(error){
  if(timedOut)throw new Error(timeoutMessage(timeoutMs));
  if(controller.signal.aborted){
   if(error instanceof Error&&error.name==="AbortError")throw error;
   throw new DOMException("The request was cancelled.","AbortError");
  }
  throw error;
 }finally{
  clearTimeout(timeoutId);
  externalSignal?.removeEventListener("abort",abortFromCaller);
 }
}
