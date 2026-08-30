import {authMode,beginLogin,getAccessToken} from "@/services/auth";

export const API=process.env.NEXT_PUBLIC_API_URL||"http://127.0.0.1:8000/api/v1";
export const DEFAULT_REQUEST_TIMEOUT_MS=30000;

export type ApiRequestInit=RequestInit&{timeoutMs?:number;retries?:number};

export class ApiError extends Error{
 status:number;
 requestId:string|null;
 constructor(message:string,status:number,requestId:string|null=null){super(message);this.name="ApiError";this.status=status;this.requestId=requestId}
}

export class AuthTransitionError extends Error{
 constructor(message:string){super(message);this.name="AuthTransitionError"}
}

type ResponseLifecycle={finish:()=>void;timedOut:()=>boolean;timeoutMs:number};
const responseLifecycles=new WeakMap<Response,ResponseLifecycle>();

function timeoutMessage(timeoutMs:number){
 const seconds=Math.max(1,Math.round(timeoutMs/1000));
 return `The service did not respond within ${seconds} seconds. Please try again.`;
}

async function authHeaders(init:ApiRequestInit){
 const mode=authMode();
 const headers=new Headers(init.headers||{});
 if(!(init.body instanceof FormData)&&!headers.has("Content-Type"))headers.set("Content-Type","application/json");
 if(mode==="development_header"){
  headers.set("X-User-ID","1");
 }else if(mode==="oidc"){
  const token=getAccessToken();
  if(!token){
   if(typeof window!=="undefined")await beginLogin(window.location.pathname+window.location.search);
   throw new AuthTransitionError("Enterprise authentication is required");
  }
  headers.set("Authorization","Bearer "+token);
 }else{
  throw new Error("Unsupported frontend authentication mode");
 }
 return {mode,headers};
}

function finishResponse(r:Response){
 responseLifecycles.get(r)?.finish();
 responseLifecycles.delete(r);
}

async function consumeBody<T>(r:Response,reader:()=>Promise<T>):Promise<T>{
 const lifecycle=responseLifecycles.get(r);
 try{
  return await reader();
 }catch(error){
  if(lifecycle?.timedOut())throw new Error(timeoutMessage(lifecycle.timeoutMs));
  throw error;
 }finally{
  finishResponse(r);
 }
}

async function readJson<T=any>(r:Response):Promise<T>{
 return consumeBody(r,()=>r.json() as Promise<T>);
}

async function readBlob(r:Response):Promise<Blob>{
 return consumeBody(r,()=>r.blob());
}

export async function authenticatedFetch(path:string,init:ApiRequestInit={}):Promise<Response>{
 const {mode,headers}=await authHeaders(init);
 const timeoutMs=Math.max(1,init.timeoutMs??DEFAULT_REQUEST_TIMEOUT_MS);
 const controller=new AbortController();
 let timedOut=false;
 const timeoutId=setTimeout(()=>{timedOut=true;controller.abort()},timeoutMs);
 const externalSignal=init.signal;
 const abortFromCaller=()=>controller.abort();
 let finished=false;
 const finish=()=>{
  if(finished)return;
  finished=true;
  clearTimeout(timeoutId);
  externalSignal?.removeEventListener("abort",abortFromCaller);
 };
 if(externalSignal){
  if(externalSignal.aborted)controller.abort();
  else externalSignal.addEventListener("abort",abortFromCaller,{once:true});
 }
 const {timeoutMs:_timeoutMs,retries:_retries,signal:_signal,...fetchInit}=init;
 try{
  const r=await fetch(API+path,{...fetchInit,headers,signal:controller.signal});
  if(r.status===401&&mode==="oidc"&&typeof window!=="undefined"){
   finish();
   await beginLogin(window.location.pathname+window.location.search);
   throw new AuthTransitionError("Enterprise session expired");
  }
  responseLifecycles.set(r,{finish,timedOut:()=>timedOut,timeoutMs});
  return r;
 }catch(error){
  finish();
  if(timedOut)throw new Error(timeoutMessage(timeoutMs));
  if(controller.signal.aborted){
   if(error instanceof Error&&error.name==="AbortError")throw error;
   throw new DOMException("The request was cancelled.","AbortError");
  }
  throw error;
 }
}

async function responseError(r:Response,fallback="Request failed"){
 const e=await readJson<{detail?:string}>(r).catch(()=>({detail:fallback}));
 return new ApiError(e.detail||fallback,r.status,r.headers.get("x-request-id"));
}

function filenameFromDisposition(disposition:string,fallbackFilename:string){
 const extended=disposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
 if(extended){
  const value=extended[1].trim().replace(/^"|"$/g,"");
  try{return decodeURIComponent(value)}catch{return value}
 }
 const quoted=disposition.match(/filename\s*=\s*"([^"]*)"/i);
 if(quoted)return quoted[1];
 const plain=disposition.match(/filename\s*=\s*([^;]+)/i);
 return (plain?.[1]||fallbackFilename).trim();
}

export async function request<T>(path:string,init:ApiRequestInit={}):Promise<T>{
 const method=(init.method||"GET").toUpperCase();
 const retries=Math.max(0,init.retries??(method==="GET"?1:0));
 let attempt=0;
 while(true){
  try{
   const r=await authenticatedFetch(path,init);
   if(r.ok)return readJson<T>(r);
   const error=await responseError(r);
   if(r.status===403&&typeof window!=="undefined"&&!window.location.pathname.startsWith("/access-denied")){
    const from=window.location.pathname+window.location.search;
    window.location.assign("/access-denied?from="+encodeURIComponent(from)+(error.requestId?"&requestId="+encodeURIComponent(error.requestId):""));
   }
   const retryable=[429,502,503,504].includes(r.status);
   if(retryable&&attempt<retries){attempt+=1;continue}
   throw error;
  }catch(error){
   if(error instanceof ApiError||error instanceof AuthTransitionError)throw error;
   if(error instanceof Error&&error.name==="AbortError")throw error;
   if(attempt<retries){attempt+=1;continue}
   throw error;
  }
 }
}

export async function downloadFile(path:string,fallbackFilename:string,init:ApiRequestInit={}):Promise<string>{
 const r=await authenticatedFetch(path,init);
 if(!r.ok){
  const error=await responseError(r,"Download failed");
  if(r.status===403&&typeof window!=="undefined"&&!window.location.pathname.startsWith("/access-denied")){
   const from=window.location.pathname+window.location.search;
   window.location.assign("/access-denied?from="+encodeURIComponent(from)+(error.requestId?"&requestId="+encodeURIComponent(error.requestId):""));
  }
  throw error;
 }
 const blob=await readBlob(r);
 const disposition=r.headers.get("content-disposition")||"";
 const filename=filenameFromDisposition(disposition,fallbackFilename);
 const url=URL.createObjectURL(blob);
 try{
  const a=document.createElement("a");
  a.href=url;a.download=filename;a.style.display="none";
  document.body.appendChild(a);a.click();a.remove();
 }finally{
  URL.revokeObjectURL(url);
 }
 return filename;
}
