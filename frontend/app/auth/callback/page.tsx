"use client";

import {useEffect,useState} from "react";
import {handleCallback} from "@/services/auth";

export default function OidcCallbackPage(){
 const [error,setError]=useState("");
 useEffect(()=>{
  handleCallback(window.location.search)
   .then(returnTo=>window.location.replace(returnTo))
   .catch(e=>setError(e instanceof Error?e.message:"Enterprise sign-in failed."));
 },[]);
 return <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
  <div className="w-full max-w-md rounded border border-slate-200 bg-white p-6 text-center shadow-sm">
   <div className="text-sm font-bold text-[#304354]">L&T Bid Intelligence</div>
   {error?<><div className="mt-4 text-sm font-semibold text-red-700">Enterprise sign-in failed</div><div className="mt-2 text-xs text-slate-600">{error}</div></>:<><div className="mt-4 text-sm font-semibold text-slate-800">Completing secure sign-in…</div><div className="mt-2 text-xs text-slate-500">Validating the OIDC authorization response.</div></>}
  </div>
 </div>;
}
