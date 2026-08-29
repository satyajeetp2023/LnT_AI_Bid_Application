"use client";

import Link from "next/link";
import {use,useCallback,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {EmptyState,ErrorState,LoadingState,PageHeader,PriorityBadge,StatusBadge,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,PreBidQuery,PreBidQueryPage} from "@/types";

const emptySummary={total:0,draft:0,submitted:0,responded:0,open:0,overdue:0};

export default function ReviewApprovalPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [items,setItems]=useState<PreBidQuery[]>([]);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");

 const load=useCallback(()=>{
  setLoading(true);setError("");
  Promise.all([
   request<Bid>(`/bids/${id}`),
   request<PreBidQueryPage>(`/bids/${id}/pre-bid-queries?page_size=100`)
  ]).then(([b,q])=>{setBid(b);setItems(q.items)})
    .catch(()=>setError("Unable to load the review queue. Please try again."))
    .finally(()=>setLoading(false));
 },[id]);
 useEffect(load,[load]);

 const approve=async(item:PreBidQuery)=>{
  await request(`/pre-bid-queries/${item.id}/approve`,{method:"POST"});
  load();
 };

 const ready=items.filter(x=>x.status==="Ready for Review");
 const approved=items.filter(x=>x.status==="Approved");
 const submitted=items.filter(x=>["Submitted","Responded","Closed"].includes(x.status));

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Review"/>
  <PageHeader
   items={[{label:"Bid Workspace",href:"/bids"},{label:"Review & Approval"}]}
   title="Review & Approval"
   description="Approve bidder-reviewed outputs before they move into formal submission."
  />
  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
   <SummaryCard label="Ready for Review" value={ready.length} tone="amber"/>
   <SummaryCard label="Approved" value={approved.length} tone="green"/>
   <SummaryCard label="Submitted / Closed" value={submitted.length}/>
   <SummaryCard label="Total Queries" value={items.length}/>
  </div>

  {error?<ErrorState message={error}/>:loading?<LoadingState label="Loading review queue…"/>:<div className="space-y-3">
   <section className="overflow-hidden border border-slate-200 bg-white">
    <div className="border-b bg-slate-50 px-4 py-3">
     <h2 className="text-sm font-bold text-slate-900">Pre-Bid Queries Awaiting Approval</h2>
     <p className="text-xs text-slate-500">Only queries explicitly marked Ready for Review appear here.</p>
    </div>
    {ready.length===0?<EmptyState title="No queries awaiting approval" description="Move a reviewed Pre-Bid Query to Ready for Review when it is ready for formal approval."/>:
     <div className="grid gap-3 p-3 lg:grid-cols-2">
      {ready.map(x=><article key={x.id} className="rounded border border-slate-200 bg-white p-4 shadow-sm">
       <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
         <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{x.query_number||`Query #${x.id}`}</div>
         <h3 className="mt-0.5 text-sm font-semibold text-slate-900">{x.query_title}</h3>
        </div>
        <PriorityBadge value={x.priority}/>
       </div>
       <p className="mt-2 line-clamp-4 text-xs leading-5 text-slate-600">{x.query_text}</p>
       <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div><span className="text-slate-500">Category</span><div className="font-medium text-slate-800">{x.query_category}</div></div>
        <div><span className="text-slate-500">Owner</span><div className="font-medium text-slate-800">{x.responsible_function||"—"}</div></div>
        <div><span className="text-slate-500">Source</span><div className="truncate font-medium text-slate-800">{x.source_document_title||x.source_original_filename||"—"}</div></div>
        <div><span className="text-slate-500">Reference</span><div className="font-medium text-slate-800">{x.source_clause?`Cl. ${x.source_clause}`:"—"}{x.source_page?` · p.${x.source_page}`:""}</div></div>
       </div>
       <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <Link href={`/bids/${id}/pre-bid-queries`} className="rounded border border-slate-300 px-3 py-2 text-xs font-semibold text-blue-700">Open Register</Link>
        <button onClick={()=>approve(x)} className="rounded bg-[#e2b635] px-4 py-2 text-xs font-semibold text-[#243241]">Approve Query</button>
       </div>
      </article>)}
     </div>}
   </section>

   <section className="overflow-hidden border border-slate-200 bg-white">
    <div className="border-b bg-slate-50 px-4 py-3">
     <h2 className="text-sm font-bold text-slate-900">Approved Queries</h2>
     <p className="text-xs text-slate-500">Approved items remain controlled; material edits send them back to review automatically.</p>
    </div>
    {approved.length===0?<div className="px-4 py-6 text-sm text-slate-500">No approved Pre-Bid Queries yet.</div>:
     <div className="divide-y">{approved.map(x=><div key={x.id} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0"><div className="truncate text-sm font-semibold text-slate-900">{x.query_title}</div><div className="mt-1 text-xs text-slate-500">{x.query_category} · {x.responsible_function||"Unassigned"}{x.approved_at?` · approved ${new Date(x.approved_at).toLocaleString()}`:""}</div></div>
      <StatusBadge tone="green">Approved</StatusBadge>
     </div>)}</div>}
   </section>
  </div>}
 </div>;
}
