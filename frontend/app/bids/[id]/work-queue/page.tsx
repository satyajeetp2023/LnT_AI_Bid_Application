"use client";

import Link from "next/link";
import {use,useCallback,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {EmptyState,ErrorState,LoadingState,PageHeader,PriorityBadge,StatusBadge,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,DepartmentWorkQueue,ProjectMember} from "@/types";

const emptyQueue:DepartmentWorkQueue={items:[],summary:{total:0,critical:0,high:0,overdue:0,unassigned:0,without_person:0},by_function:[],by_type:[],by_person:[],filter:{responsible_function:null},version:""};

export default function WorkQueuePage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [queue,setQueue]=useState<DepartmentWorkQueue>(emptyQueue);
 const [owner,setOwner]=useState("");
 const [members,setMembers]=useState<ProjectMember[]>([]);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");

 const load=useCallback(()=>{
  setLoading(true);setError("");
  const suffix=owner?`?responsible_function=${encodeURIComponent(owner)}`:"";
  Promise.all([
   request<Bid>(`/bids/${id}`),
   request<DepartmentWorkQueue>(`/bids/${id}/department-work-queue${suffix}`),
   request<ProjectMember[]>(`/bids/${id}/members`)
  ]).then(([b,q,m])=>{setBid(b);setQueue(q);setMembers(m)})
    .catch(()=>setError("Unable to load the department work queue. Please try again."))
    .finally(()=>setLoading(false));
 },[id,owner]);
 useEffect(load,[load]);

 const assignPerson=async(entity_type:string,entity_id:number,user_id:string)=>{
  await request(`/bids/${id}/work-items/assign-person`,{method:"POST",body:JSON.stringify({entity_type,entity_id,user_id:user_id?Number(user_id):null})});
  load();
 };

 const functions=Array.from(new Set(queue.by_function.map(x=>x.name))).sort();

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Work Queue"/>
  <PageHeader
   items={[{label:"Bid Workspace",href:"/bids"},{label:"Work Queue"}]}
   title="Department Work Queue"
   description="One prioritized queue for requirements, missing inputs and Pre-Bid Queries that still need departmental action."
   action={<select aria-label="Filter by responsible function" className="rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700" value={owner} onChange={e=>setOwner(e.target.value)}><option value="">All functions</option>{functions.map(x=><option key={x}>{x}</option>)}</select>}
  />

  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-6">
   <SummaryCard label="Open Actions" value={queue.summary.total}/>
   <SummaryCard label="Critical" value={queue.summary.critical} tone="red"/>
   <SummaryCard label="High" value={queue.summary.high} tone="amber"/>
   <SummaryCard label="Overdue" value={queue.summary.overdue} tone="red"/>
   <SummaryCard label="Unassigned Function" value={queue.summary.unassigned}/>
   <SummaryCard label="No Named Owner" value={queue.summary.without_person} tone="amber"/>
  </div>

  {queue.by_function.length>0&&<section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white">
   <div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Department Load</h2><p className="text-xs text-slate-500">Open actions by responsible function.</p></div>
   <div className="flex gap-2 overflow-x-auto p-3">{queue.by_function.map(x=><button key={x.name} onClick={()=>setOwner(owner===x.name?"":x.name)} className={`min-w-[135px] rounded border p-3 text-left ${owner===x.name?"border-[#e2b635] bg-amber-50":"border-slate-200 bg-white"}`}><div className="truncate text-[10px] font-semibold uppercase tracking-wide text-slate-500">{x.name}</div><div className="mt-1 text-lg font-bold text-slate-900">{x.count}</div><div className="text-[11px] text-slate-500">open action{x.count===1?"":"s"}</div></button>)}</div>
  </section>}

  {error?<ErrorState message={error}/>:loading?<LoadingState label="Loading department work queue…"/>:queue.items.length===0?<EmptyState title="No open departmental actions" description={owner?"This function currently has no outstanding bid actions.":"All currently tracked departmental actions are closed."}/>:<>
   <div className="space-y-2 md:hidden">
    {queue.items.map((x,index)=><article key={`${x.entity_type}-${x.entity_id}`} className="rounded border border-slate-200 bg-white p-3 shadow-sm">
     <div className="flex items-start gap-3"><div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">{index+1}</div><div className="min-w-0 flex-1"><div className="text-[10px] font-semibold uppercase tracking-wide text-blue-700">{x.entity_type}</div><h3 className="mt-0.5 text-sm font-semibold text-slate-900">{x.title}</h3></div><PriorityBadge value={x.priority}/></div>
     <div className="mt-3 flex flex-wrap gap-2"><StatusBadge tone={x.is_overdue?"red":x.status==="Resolved"||x.status==="Closed"?"green":"grey"}>{x.is_overdue?`Overdue · ${x.status}`:x.status}</StatusBadge></div>
     <div className="mt-3 grid grid-cols-2 gap-3 text-xs"><div><span className="text-slate-500">Function</span><div className="font-medium text-slate-800">{x.responsible_function||"Unassigned"}</div></div><div><span className="text-slate-500">Responsible Person</span><select aria-label={`Assign ${x.title}`} className="mt-1 w-full rounded border border-slate-300 bg-white p-2 text-xs" value={members.find(m=>m.name===x.responsible_person)?.user_id||""} onChange={e=>assignPerson(x.entity_type,x.entity_id,e.target.value)}><option value="">Needs assignment</option>{members.map(m=><option key={m.user_id} value={m.user_id}>{m.name} · {m.project_role}</option>)}</select></div><div><span className="text-slate-500">Due</span><div className="font-medium text-slate-800">{x.due_date||"—"}</div></div></div>
     <div className="mt-3 rounded bg-slate-50 p-2 text-xs leading-5 text-slate-600"><span className="font-semibold text-slate-700">Next:</span> {x.action}. {x.reason}</div>
     <div className="mt-3 border-t pt-3"><Link href={x.route} className="inline-flex rounded bg-[#e2b635] px-3 py-2 text-xs font-semibold text-[#243241]">Open Register</Link></div>
    </article>)}
   </div>

   <section className="hidden overflow-hidden border border-slate-200 bg-white md:block">
    <div className="overflow-x-auto"><table className="w-full min-w-[1100px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{["#","Work Item","Type","Priority","Status","Function","Responsible Person","Due","Next Action","Source",""].map(x=><th key={x} className="px-3 py-3">{x}</th>)}</tr></thead><tbody>{queue.items.map((x,index)=><tr key={`${x.entity_type}-${x.entity_id}`} className="border-t align-top"><td className="px-3 py-3 text-xs font-bold text-slate-500">{index+1}</td><td className="max-w-xs px-3 py-3"><div className="font-semibold text-slate-900">{x.title}</div><div className="mt-1 line-clamp-2 text-xs text-slate-500">{x.reason}</div></td><td className="px-3 py-3 text-xs">{x.entity_type}</td><td className="px-3 py-3"><PriorityBadge value={x.priority}/></td><td className="px-3 py-3"><StatusBadge tone={x.is_overdue?"red":"grey"}>{x.is_overdue?`Overdue · ${x.status}`:x.status}</StatusBadge></td><td className="px-3 py-3 text-xs">{x.responsible_function||"Unassigned"}</td><td className="px-3 py-3"><select aria-label={`Assign ${x.title}`} className={"max-w-[190px] rounded border bg-white p-1.5 text-xs "+(x.responsible_person?"border-slate-300 text-slate-700":"border-amber-300 text-amber-700")} value={members.find(m=>m.name===x.responsible_person)?.user_id||""} onChange={e=>assignPerson(x.entity_type,x.entity_id,e.target.value)}><option value="">Needs assignment</option>{members.map(m=><option key={m.user_id} value={m.user_id}>{m.name} · {m.project_role}</option>)}</select></td><td className="whitespace-nowrap px-3 py-3 text-xs">{x.due_date||"—"}</td><td className="max-w-xs px-3 py-3 text-xs text-slate-600">{x.action}</td><td className="max-w-40 px-3 py-3 text-xs text-slate-500"><div className="truncate">{x.source_document||"—"}</div>{(x.source_page||x.source_clause)&&<div>{x.source_page&&`p.${x.source_page}`}{x.source_page&&x.source_clause&&" · "}{x.source_clause&&`Cl.${x.source_clause}`}</div>}</td><td className="whitespace-nowrap px-3 py-3"><Link href={x.route} className="font-semibold text-blue-700">Open</Link></td></tr>)}</tbody></table></div>
   </section>
  </>}
 </div>;
}
