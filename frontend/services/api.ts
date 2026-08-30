import {authMode,beginLogin,getAccessToken} from "@/services/auth";

export const API=process.env.NEXT_PUBLIC_API_URL||"http://127.0.0.1:8000/api/v1";

export async function request<T>(path:string,init?:RequestInit):Promise<T>{
 const mode=authMode();
 const headers=new Headers(init?.headers||{});
 if(!(init?.body instanceof FormData)&&!headers.has("Content-Type"))headers.set("Content-Type","application/json");
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
 const r=await fetch(API+path,{...init,headers});
 if(r.status===401&&mode==="oidc"&&typeof window!=="undefined"){
  await beginLogin(window.location.pathname+window.location.search);
  throw new Error("Enterprise session expired");
 }
 if(!r.ok){
  const e=await r.json().catch(()=>({detail:"Request failed"}));
  throw new Error(e.detail||"Request failed");
 }
 return r.json();
}
