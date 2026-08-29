"use client";

import Link from "next/link";
import {use,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {EmptyState,ErrorState,LoadingState,PageHeader,PriorityBadge,SourceEvidenceCard,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,SubmissionFormatCandidateResponse} from "@/types";

const empty:SubmissionFormatCandidateResponse={items:[],summary:{detected:0,mandatory:0,high_priority:0,with_source:0},version:""};

export default function BidPreparationPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [data,setData]=useState<SubmissionFormatCandidateResponse>(empty);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");
 useEffect(()=>{
  setLoading(true);
  Promise.all([
   request<Bid>(`/bids/${id}`),
   request<SubmissionFormatCandidateResponse>(`/bids/${id}/submission-format-candidates`)
  ]).then(([b,d])=>{setBid(b);setData(d)}).catch(()=>setError("Unable to load submission format intelligence.")).finally(()=>setLoading(false));
 },[id]);

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Bid Preparation"/>
  <PageHeader items={[{label:"Bid Workspace",href:"/bids"},{label:"Bid Preparation"}]} title="Bid Preparation" description="Review employer-prescribed forms, annexures, schedules and submission formats detected from tender requirements."/>
  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
   <SummaryCard label="Detected Formats" value={data.summary.detected}/>
   <SummaryCard label="Mandatory" value={data.summary.mandatory} tone="red"/>
   <SummaryCard label="High Priority" value={data.summary.high_priority} tone="amber"/>
   <SummaryCard label="With Source Traceability" value={data.summary.with_source} tone="green"/>
  </div>
  {error?<ErrorState message={error}/>:loading?<LoadingState label="Scanning extracted requirements for employer-prescribed formats…"/>:data.items.length===0?<EmptyState title="No prescribed submission formats detected yet" description="Formats will appear here automatically when extracted tender requirements refer to forms, annexures, schedules, appendices or prescribed templates."/>:<section className="grid gap-3 lg:grid-cols-2">
   {data.items.map(x=><article key={`${x.requirement_id}-${x.format_name}`} className="rounded border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="text-[10px] font-bold uppercase tracking-wide text-blue-700">{x.format_kind}</div><h2 className="mt-0.5 text-sm font-semibold text-slate-900">{x.format_name}</h2></div><PriorityBadge value={x.priority}/></div>
    <div className="mt-2 text-xs leading-5 text-slate-600">{x.requirement_text}</div>
    <div className="mt-3 flex flex-wrap gap-2 text-[11px]"><span className="rounded bg-slate-100 px-2 py-1 font-semibold text-slate-700">{x.status}</span>{x.mandatory&&<span className="rounded bg-red-50 px-2 py-1 font-semibold text-red-700">Mandatory</span>}<span className="rounded bg-blue-50 px-2 py-1 font-semibold text-blue-700">{Math.round(x.confidence*100)}% detection confidence</span></div>
    <div className="mt-3 rounded bg-slate-50 p-2 text-xs leading-5 text-slate-600"><span className="font-semibold text-slate-700">Next:</span> {x.next_action}</div>
    <div className="mt-3"><SourceEvidenceCard document={x.source_document||"No source document"} page={x.source_page} clause={x.source_clause} section={x.source_section} excerpt={x.source_excerpt}/></div>
    <div className="mt-3 flex flex-wrap gap-2 border-t pt-3"><Link href={`/bids/${id}/requirements`} className="rounded border border-slate-300 px-3 py-2 text-xs font-semibold text-blue-700">Open Requirement</Link>{x.source_document_id&&<Link href={`/bids/${id}/documents`} className="rounded border border-slate-300 px-3 py-2 text-xs font-semibold text-blue-700">Open Documents</Link>}</div>
   </article>)}
  </section>}
 </div>;
}
