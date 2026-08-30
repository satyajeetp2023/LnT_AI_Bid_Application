"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {useEffect,useMemo,useState} from "react";
import {
 BarChart3,ChevronRight,FileCheck2,FileQuestion,FileSearch,Files,FolderKanban,
 History,LayoutDashboard,LockKeyhole,PlusSquare,Search,Settings,ShieldCheck,
 Sparkles,TriangleAlert,Workflow,X
} from "lucide-react";

type NavItem={n:string;h?:string;i:any;keywords?:string};
type NavGroup={id:string;n:string;i:any;description:string;items:NavItem[]};

export function Sidebar({mobileOpen=false,onClose}:{mobileOpen?:boolean;onClose?:()=>void}){
 const p=usePathname();
 const bidMatch=p.match(/^\/bids\/([^/]+)(?:\/|$)/);
 const bidId=bidMatch?.[1];
 const [activeGroup,setActiveGroup]=useState<string|null>(null);
 const [query,setQuery]=useState("");

 const groups:NavGroup[]=useMemo(()=>[
  {id:"overview",n:"Overview",i:LayoutDashboard,description:"Bid portfolio and setup",items:[
   {n:"Dashboard",h:"/",i:LayoutDashboard,keywords:"home overview"},
   {n:"My Bids",h:"/bids",i:FolderKanban,keywords:"projects tender list"},
   {n:"Create New Bid",h:"/bids/new",i:PlusSquare,keywords:"new project tender"},
  ]},
  {id:"intelligence",n:"Tender Intelligence",i:Sparkles,description:"Read, understand and challenge the tender",items:[
   {n:"Document Repository",h:bidId?`/bids/${bidId}/documents`:undefined,i:Files,keywords:"upload tender files repository"},
   {n:"Requirement Register",h:bidId?`/bids/${bidId}/requirements`:undefined,i:FileSearch,keywords:"clauses requirements scope"},
   {n:"Missing Inputs",h:bidId?`/bids/${bidId}/missing-inputs`:undefined,i:TriangleAlert,keywords:"gaps estimation readiness"},
   {n:"Pre-Bid Queries",h:bidId?`/bids/${bidId}/pre-bid-queries`:undefined,i:FileQuestion,keywords:"pbq clarification queries"},
   {n:"Bid Intelligence Copilot",h:bidId?`/bids/${bidId}/copilot`:undefined,i:Sparkles,keywords:"chat tender clause risk drawing boq ai"},
  ]},
  {id:"preparation",n:"Planning & Preparation",i:Workflow,description:"Prepare, plan and coordinate the bid",items:[
   {n:"Work Queue",h:bidId?`/bids/${bidId}/work-queue`:undefined,i:FileCheck2,keywords:"department actions ownership"},
   {n:"Bid Preparation",h:bidId?`/bids/${bidId}/bid-preparation`:undefined,i:FileCheck2,keywords:"formats templates employer"},
   {n:"Schedules",h:bidId?`/bids/${bidId}/schedules`:undefined,i:FileCheck2,keywords:"primavera p6 programme resource planning"},
  ]},
  {id:"review",n:"Review & Insights",i:ShieldCheck,description:"Approve, submit and learn",items:[
   {n:"Review & Approval",h:bidId?`/bids/${bidId}/review-approval`:undefined,i:ShieldCheck,keywords:"approval management gate"},
   {n:"Submission",h:bidId?`/bids/${bidId}/submission`:undefined,i:FileCheck2,keywords:"package final submission"},
   {n:"Bid Results",h:bidId?`/bids/${bidId}/bid-results`:undefined,i:BarChart3,keywords:"win loss result l1 l2 l3 l4"},
   {n:"Historical Intelligence",h:"/historical-intelligence",i:History,keywords:"history previous bids benchmark win loss competitor"},
   {n:"Reports & Analytics",i:BarChart3,keywords:"dashboard reports analytics"},
  ]},
 ],[bidId]);

 const allItems=useMemo(()=>groups.flatMap(g=>g.items.map(item=>({...item,group:g.n,groupId:g.id}))),[groups]);
 const normalized=query.trim().toLowerCase();
 const searchResults=useMemo(()=>normalized?allItems.filter(x=>
  `${x.n} ${x.group} ${x.keywords||""}`.toLowerCase().includes(normalized)
 ).slice(0,10):[],[allItems,normalized]);

 const selected=(h?:string)=>{
  if(!h)return false;
  if(h==="/")return p==="/";
  if(h==="/bids")return p==="/bids";
  if(h==="/bids/new")return p==="/bids/new";
  return p===h||p.startsWith(h+"/");
 };
 const routeGroup=groups.find(g=>g.items.some(x=>selected(x.h)))?.id||null;

 useEffect(()=>{
  setQuery("");
  setActiveGroup(null);
 },[p]);

 const renderItem=(x:NavItem,theme:"dark"|"light"="dark")=>{
  const isSelected=selected(x.h);
  const light=theme==="light";
  if(x.h)return <Link key={x.n} href={x.h} onClick={()=>{setActiveGroup(null);setQuery("");onClose?.()}} className={`flex min-h-[38px] items-center gap-3 rounded px-3 py-2 text-[11.5px] transition ${isSelected?"bg-[#e2b635] font-semibold text-[#263442]":light?"text-slate-700 hover:bg-slate-100 hover:text-[#243241]":"text-slate-200 hover:bg-white/10 hover:text-white"}`}>
   <x.i size={14} strokeWidth={isSelected?2.2:1.8}/><span className="min-w-0 flex-1 truncate">{x.n}</span>
  </Link>;
  return <div key={x.n} aria-disabled="true" className={`flex min-h-[38px] items-center gap-3 rounded px-3 py-2 text-[11px] ${light?"text-slate-400":"text-slate-400"}`}>
   <x.i size={13.5}/><span className="min-w-0 flex-1 truncate">{x.n}</span><LockKeyhole size={9}/>
  </div>;
 };

 const active=groups.find(g=>g.id===activeGroup);
 const showFlyout=Boolean(active||normalized);

 return <div>
  <button aria-label="Close navigation" onClick={onClose} className={`fixed inset-0 top-[58px] z-30 bg-black/40 transition md:hidden ${mobileOpen?"block":"hidden"}`}/>

  <aside className={`fixed bottom-0 left-0 top-[58px] z-40 flex w-[264px] flex-col border-r border-[#445565] bg-[#304354] text-white transition-transform duration-200 md:w-[204px] md:translate-x-0 ${mobileOpen?"translate-x-0":"-translate-x-full"} md:flex`}>
   <div className="border-b border-white/10 p-3">
    <div className="relative">
     <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"/>
     <input
      value={query}
      onChange={e=>{setQuery(e.target.value);if(e.target.value)setActiveGroup(null)}}
      placeholder="Search modules..."
      aria-label="Search navigation modules"
      className="h-9 w-full rounded border border-white/15 bg-[#263947] pl-8 pr-8 text-[11px] text-white outline-none placeholder:text-slate-400 focus:border-[#e2b635]"
     />
     {query&&<button aria-label="Clear search" onClick={()=>setQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"><X size={12}/></button>}
    </div>
   </div>

   <nav className="flex-1 overflow-y-auto px-3 py-3">
    <div className="mb-2 px-1 text-[8.5px] font-bold uppercase tracking-[.16em] text-slate-400">Workspace</div>
    <div className="space-y-1">
     {groups.map(group=>{
      const isOpen=activeGroup===group.id;
      const containsRoute=routeGroup===group.id;
      return <div key={group.id}>
       <button onClick={()=>{setQuery("");setActiveGroup(isOpen?null:group.id)}} className={`flex w-full items-center gap-3 rounded px-3 py-2.5 text-left transition ${isOpen?"bg-white/12 text-white":containsRoute?"bg-white/8 text-[#f3cc58]":"text-slate-200 hover:bg-white/8 hover:text-white"}`}>
        <group.i size={15}/><span className="min-w-0 flex-1"><span className="block truncate text-[11.8px] font-semibold">{group.n}</span><span className="mt-0.5 hidden truncate text-[8.5px] font-normal text-slate-400 md:block">{group.description}</span></span><ChevronRight size={13} className={`transition-transform md:rotate-0 ${isOpen?"rotate-90":""}`}/>
       </button>
       {isOpen&&<div className="mt-1 space-y-0.5 rounded bg-[#293b49] p-1.5 md:hidden">{group.items.map(x=>renderItem(x,"dark"))}</div>}
      </div>
     })}
    </div>
   </nav>

   <div className="border-t border-white/10 p-3">
    <Link href="/settings" onClick={onClose} className="flex h-[34px] items-center gap-3 rounded px-3 text-[11.8px] text-slate-200 hover:bg-white/10 hover:text-white"><Settings size={14}/>Settings</Link>
    <div className="px-3 pt-2 text-[8.5px] font-semibold italic tracking-wide text-[#e2b635]">Engineering the Change</div>
   </div>
  </aside>

  {showFlyout&&<section
   className="fixed left-[216px] z-50 hidden w-[292px] overflow-hidden rounded-lg border border-slate-200 bg-white text-slate-800 shadow-[0_12px_34px_rgba(15,23,42,.20)] md:block"
   style={{top:normalized?72:Math.min(430,132+Math.max(0,groups.findIndex(g=>g.id===activeGroup))*52)}}
  >
   <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
    <div className="text-[9px] font-bold uppercase tracking-[.15em] text-slate-400">{normalized?"Search Navigation":"Navigation Group"}</div>
    <div className="mt-1 text-sm font-semibold text-[#243241]">{normalized?`Results for “${query.trim()}”`:active?.n}</div>
    {!normalized&&active&&<div className="mt-1 text-[10px] leading-4 text-slate-500">{active.description}</div>}
   </div>
   <div className="max-h-[420px] overflow-y-auto p-2">
    {normalized?(
     searchResults.length?<div className="space-y-1">{searchResults.map(x=><div key={x.groupId+"-"+x.n}><div className="px-3 pb-1 pt-2 text-[8px] font-bold uppercase tracking-wide text-slate-400">{x.group}</div>{renderItem(x,"light")}</div>)}</div>:
     <div className="p-4 text-xs text-slate-500">No matching module found.</div>
    ):active?<div className="space-y-1">{active.items.map(x=>renderItem(x,"light"))}</div>:null}
   </div>
   {!bidId&&active&&active.id!=="overview"&&<div className="border-t border-amber-200 bg-amber-50 p-3 text-[10px] leading-4 text-amber-800">Open a bid first to access bid-specific modules.</div>}
  </section>}
 </div>
}
