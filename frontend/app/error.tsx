"use client";

import Link from "next/link";
import {useEffect} from "react";
import {TriangleAlert} from "lucide-react";

export default function GlobalError({error,reset}:{error:Error&{digest?:string;requestId?:string|null};reset:()=>void}){
 useEffect(()=>{console.error("Unhandled application error",error)},[error]);
 return <div className="mx-auto max-w-2xl py-12">
  <div className="rounded-lg border border-amber-200 bg-white p-8 text-center shadow-sm">
   <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-amber-50 text-amber-700"><TriangleAlert size={24}/></div>
   <h1 className="mt-4 text-xl font-bold text-slate-900">Something went wrong</h1>
   <p className="mt-2 text-sm leading-6 text-slate-600">The application could not complete this screen. Your saved bid data has not been intentionally changed by this error.</p>
   {(error.requestId||error.digest)&&<div className="mt-3 text-[11px] text-slate-500">Reference: <span className="font-mono">{error.requestId||error.digest}</span></div>}
   <div className="mt-6 flex flex-wrap justify-center gap-2">
    <button onClick={reset} className="rounded bg-[#304354] px-4 py-2 text-sm font-semibold text-white">Try Again</button>
    <Link href="/" className="rounded border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Dashboard</Link>
   </div>
  </div>
 </div>;
}
