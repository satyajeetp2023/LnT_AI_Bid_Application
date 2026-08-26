"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {BarChart3,FileCheck2,FileQuestion,FileSearch,Files,FolderKanban,History,LayoutDashboard,LockKeyhole,PlusSquare,Settings,ShieldCheck,TriangleAlert} from "lucide-react";
import {LTConstructionLogo} from "@/components/LTConstructionLogo";

const management=[
 {n:"Dashboard",h:"/",i:LayoutDashboard},
 {n:"My Bids",h:"/bids",i:FolderKanban},
 {n:"Create New Bid",h:"/bids/new",i:PlusSquare},
];

export function Sidebar(){
 const p=usePathname();
 const bidMatch=p.match(/^\/bids\/([^/]+)(?:\/|$)/);
 const bidId=bidMatch?.[1];
 const workspace=[
  {n:"Document Repository",h:bidId?`/bids/${bidId}/documents`:undefined,i:Files},
  {n:"Requirement Register",h:bidId?`/bids/${bidId}/requirements`:undefined,i:FileSearch},
  {n:"Missing Inputs",h:bidId?`/bids/${bidId}/missing-inputs`:undefined,i:TriangleAlert},
  {n:"Pre-Bid Queries",h:bidId?`/bids/${bidId}/pre-bid-queries`:undefined,i:FileQuestion},
 ];
 const future=[
  {n:"Schedules",i:FileCheck2},
  {n:"Bid Preparation",i:FileCheck2},
  {n:"Review & Approval",i:ShieldCheck},
  {n:"Submission",i:FileCheck2},
  {n:"Bid Results",i:BarChart3},
  {n:"Historical Intelligence",i:History},
  {n:"Reports & Analytics",i:BarChart3},
 ];
 const item=(x:any)=>{
  const selected=x.h?(x.h==="/"?p===x.h:p===x.h||p.startsWith(x.h+"/")):false;
  if(x.h)return <Link key={x.n} href={x.h} className={`group flex items-center gap-3 rounded-sm px-3 py-2 text-[12.5px] transition ${selected?"bg-[#d5aa35] font-semibold text-[#243241]":"text-slate-200 hover:bg-white/8 hover:text-white"}`}><x.i size={15} strokeWidth={selected?2.2:1.8}/><span>{x.n}</span></Link>;
  return <div key={x.n} aria-disabled="true" className="flex items-center justify-between rounded-sm px-3 py-2 text-[12px] text-slate-400"><span className="flex items-center gap-3"><x.i size={14}/>{x.n}</span><LockKeyhole size={10}/></div>;
 };
 return <aside className="fixed hidden h-screen w-[230px] flex-col bg-[#2f4050] text-white md:flex">
  <div className="flex h-16 items-center bg-[#d5aa35] px-3.5">
   <LTConstructionLogo className="h-[34px] w-auto max-w-[188px] object-contain"/>
  </div>
  <nav className="flex-1 overflow-y-auto px-3 py-4">
   <div className="nav-label">Navigation</div>
   <div className="space-y-0.5">{management.map(item)}</div>
   <div className="mt-3 space-y-0.5">{workspace.map(item)}</div>
   <div className="mt-1 space-y-0.5">{future.map(item)}</div>
  </nav>
  <div className="border-t border-white/10 p-3">
   <Link href="/settings" className="flex items-center gap-3 rounded-sm px-3 py-2 text-[12.5px] text-slate-200 hover:bg-white/8 hover:text-white"><Settings size={15}/>Settings</Link>
   <div className="mt-3 px-3 pb-1 text-[9px] font-semibold italic tracking-wide text-[#d5aa35]">Engineering the Change</div>
  </div>
 </aside>
}
