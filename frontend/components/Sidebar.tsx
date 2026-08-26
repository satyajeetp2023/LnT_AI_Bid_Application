"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {FileQuestion,FileSearch,Files,FolderKanban,LayoutDashboard,LockKeyhole,PlusSquare,Settings,ShieldCheck,TriangleAlert} from "lucide-react";
import {LTConstructionLogo} from "@/components/LTConstructionLogo";

const management=[{n:"Dashboard",h:"/",i:LayoutDashboard},{n:"My Bids",h:"/bids",i:FolderKanban},{n:"Create New Bid",h:"/bids/new",i:PlusSquare}];
const future=["Reviews","Submission"];

export function Sidebar(){
 const p=usePathname();
 const bidMatch=p.match(/^\/bids\/([^/]+)(?:\/|$)/);
 const bidId=bidMatch?.[1];
 const workspace=[
  {n:"Documents",h:bidId?`/bids/${bidId}/documents`:undefined,i:Files},
  {n:"Requirement Register",h:bidId?`/bids/${bidId}/requirements`:undefined,i:FileSearch},
  {n:"Missing Inputs",h:bidId?`/bids/${bidId}/missing-inputs`:undefined,i:TriangleAlert},
  {n:"Pre-Bid Queries",h:bidId?`/bids/${bidId}/pre-bid-queries`:undefined,i:FileQuestion},
 ];
 const item=(x:any)=>{
  const selected=x.h?(x.h==="/"?p===x.h:p===x.h||p.startsWith(x.h+"/")):false;
  if(x.h)return <Link key={x.n} href={x.h} className={`group mb-1 flex items-center gap-3 rounded-md px-3 py-2.5 text-[13px] transition ${selected?"bg-[#005596] font-semibold text-white shadow-sm":"text-slate-300 hover:bg-white/10 hover:text-white"}`}><x.i size={16} strokeWidth={selected?2.2:1.8}/><span>{x.n}</span></Link>;
  return <div key={x.n} aria-disabled="true" className="mb-1 flex items-center gap-3 rounded-md px-3 py-2.5 text-[13px] text-slate-500"><x.i size={16}/>{x.n}</div>;
 };
 return <aside className="fixed hidden h-screen w-64 flex-col border-r border-slate-200 bg-[#0b2f4f] text-white shadow-[3px_0_14px_rgba(15,23,42,.08)] md:flex">
  <div className="bg-white px-4 py-4">
   <LTConstructionLogo className="h-auto w-full max-w-[210px] object-contain"/>
  </div>
  <div className="border-y border-white/10 bg-[#082744] px-5 py-3">
   <div className="text-[13px] font-semibold tracking-wide text-white">Railway Bid Intelligence</div>
   <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[.2em] text-[#8fc4e8]">Tender Intelligence Workspace</div>
  </div>
  <nav className="flex-1 overflow-y-auto px-3 py-4">
   <div className="nav-label">Bid Management</div>{management.map(item)}
   <div className="nav-label mt-5">Bid Workspace</div>{workspace.map(item)}
   {future.map(n=><div key={n} className="flex items-center justify-between rounded-md px-3 py-2.5 text-[12px] text-slate-500"><span>{n}</span><LockKeyhole size={11}/></div>)}
   <div className="nav-label mt-5">Governance</div>{item({n:"Audit Log",h:"/audit",i:ShieldCheck})}
  </nav>
  <Link href="/settings" className="m-3 flex items-center gap-3 rounded-md border-t border-white/10 px-3 py-3 text-[13px] text-slate-300 hover:bg-white/5 hover:text-white"><Settings size={16}/>Settings</Link>
 </aside>
}
