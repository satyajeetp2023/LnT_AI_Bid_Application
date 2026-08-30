"use client";

import Link from "next/link";
import {useSearchParams} from "next/navigation";
import {ShieldX} from "lucide-react";

export default function AccessDeniedPage(){
 const params=useSearchParams();
 const from=params.get("from");
 const requestId=params.get("requestId");
 return <div className="mx-auto max-w-2xl py-12">
  <div className="rounded-lg border border-red-200 bg-white p-8 text-center shadow-sm">
   <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-red-50 text-red-700"><ShieldX size={24}/></div>
   <h1 className="mt-4 text-xl font-bold text-slate-900">Access Denied</h1>
   <p className="mt-2 text-sm leading-6 text-slate-600">Your authenticated account does not have permission to open this area. Access depends on your role and, for bid-specific modules, assignment to that bid.</p>
   {from&&<div className="mt-3 rounded bg-slate-50 p-2 text-xs text-slate-500">Requested location: <span className="font-mono">{from}</span></div>}
   {requestId&&<div className="mt-2 text-[11px] text-slate-500">Request ID: <span className="font-mono">{requestId}</span></div>}
   <div className="mt-6 flex flex-wrap justify-center gap-2">
    <Link href="/bids" className="rounded bg-[#304354] px-4 py-2 text-sm font-semibold text-white">Open My Bids</Link>
    <Link href="/settings#help" className="rounded border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Help</Link>
   </div>
  </div>
 </div>;
}
