"use client";

import Link from "next/link";
import {use,useCallback,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {EmptyState,ErrorState,LoadingState,PageHeader,PriorityBadge,StatusBadge,SummaryCard} from "@/components/design-system";
import {API,request} from "@/services/api";
import type {Bid,SubmissionReadiness} from "@/types";

export default function SubmissionPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [data,setData]=useState<SubmissionReadiness|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");
 const [packaging,setPackaging]=useState(false);

 const load=useCallback(()=>{
  setLoading(true);setError("");
  Promise.all([
   request<Bid>("/bids/"+id),
   request<SubmissionReadiness>("/bids/"+id+"/submission-readiness")
  ]).then(([b,r])=>{setBid(b);setData(r)}).catch(()=>setError("Unable to load submission readiness.")).finally(()=>setLoading(false));
 },[id]);
 useEffect(load,[load]);

 const downloadPackage=async()=>{
  setPackaging(true);setError("");
  try{
   const r=await fetch(API+"/bids/"+id+"/submission-package",{method:"POST",headers:{"X-User-ID":"1"}});
   if(!r.ok){const e=await r.json().catch(()=>({detail:"Package generation failed"}));throw new Error(e.detail||"Package generation failed")}
   const blob=await r.blob();
   const disposition=r.headers.get("content-disposition")||"";
   const match=disposition.match(/filename="?([^";]+)"?/i);
   const filename=match?.[1]||"submission_package.zip";
   const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
  }catch(e){setError(e instanceof Error?e.message:"Unable to generate submission package.")}
  finally{setPackaging(false)}
 };

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Submission"/>
  <PageHeader items={[{label:"Bid Workspace",href:"/bids"},{label:"Submission"}]} title="Submission Readiness" description="Confirm mandatory employer-format coverage and build a controlled package from approved bid artifacts." action={<button disabled={!data?.ready||packaging} onClick={downloadPackage} className="rounded bg-[#304354] px-4 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">{packaging?"Building Package…":"Build Submission ZIP"}</button>}/>

  {error&&<div className="mb-3"><ErrorState message={error}/></div>}
  {loading?<LoadingState label="Checking submission readiness…"/>:!data?<EmptyState title="Submission readiness unavailable" description="The submission readiness engine did not return a result."/>:<>
   <section className={"mb-3 overflow-hidden rounded border "+(data.ready?"border-emerald-200 bg-emerald-50":"border-amber-200 bg-amber-50")}><div className="grid gap-3 p-4 md:grid-cols-[180px_1fr_auto] md:items-center"><div><div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Submission Status</div><div className={"mt-1 text-xl font-bold "+(data.ready?"text-emerald-700":"text-amber-700")}>{data.grade}</div><div className="mt-1 text-xs text-slate-600">Estimation readiness {Math.round(data.estimation_readiness.overall_score)}% · {data.estimation_readiness.grade}</div></div><div className="text-xs leading-5 text-slate-700">{data.ready?"All detected mandatory employer formats have an approved prepared version. A controlled package can now be generated.":"Mandatory submission-format blockers remain. Resolve them before packaging."}</div><Link href={"/bids/"+id+"/bid-preparation"} className="inline-flex rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-blue-700">Open Bid Preparation</Link></div></section>

   <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-6">
    <SummaryCard label="Detected Formats" value={data.summary.detected_formats}/>
    <SummaryCard label="Mandatory" value={data.summary.mandatory_formats}/>
    <SummaryCard label="Approved Formats" value={data.summary.approved_formats} tone="green"/>
    <SummaryCard label="Mandatory Blockers" value={data.summary.mandatory_blockers} tone="red"/>
    <SummaryCard label="Warnings" value={data.summary.warnings} tone="amber"/>
    <SummaryCard label="Approved Artifacts" value={data.summary.approved_artifacts} tone="green"/>
   </div>

   {(data.blockers.length>0||data.warnings.length>0)&&<section className="mb-3 grid gap-3 lg:grid-cols-2">
    <div className="overflow-hidden rounded border border-red-200 bg-white"><div className="border-b border-red-100 bg-red-50 px-4 py-3"><h2 className="text-sm font-bold text-red-800">Blocking Issues</h2></div>{data.blockers.length===0?<div className="p-4 text-sm text-slate-500">No mandatory blockers.</div>:<div className="divide-y">{data.blockers.map((x,i)=><div key={i} className="px-4 py-3 text-xs text-red-700">{x}</div>)}</div>}</div>
    <div className="overflow-hidden rounded border border-amber-200 bg-white"><div className="border-b border-amber-100 bg-amber-50 px-4 py-3"><h2 className="text-sm font-bold text-amber-800">Warnings / Confirmation</h2></div>{data.warnings.length===0?<div className="p-4 text-sm text-slate-500">No warnings.</div>:<div className="divide-y">{data.warnings.map((x,i)=><div key={i} className="px-4 py-3 text-xs text-amber-800">{x}</div>)}</div>}</div>
   </section>}

   <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Employer Format Coverage</h2><p className="text-xs text-slate-500">Detected prescribed formats and their current preparation/approval state.</p></div>
    {data.formats.length===0?<EmptyState title="No employer formats detected" description="Confirm the tender package manually or return to Bid Preparation when formats become available."/>:<>
     <div className="space-y-2 p-3 md:hidden">{data.formats.map(x=><article key={x.requirement_id} className="rounded border border-slate-200 p-3"><div className="flex items-start justify-between gap-2"><div><div className="text-[10px] font-bold uppercase tracking-wide text-blue-700">{x.format_kind}</div><div className="mt-0.5 text-sm font-semibold text-slate-900">{x.format_name}</div></div><PriorityBadge value={x.priority}/></div><div className="mt-2 flex flex-wrap gap-2"><StatusBadge tone={x.status==="Approved"?"green":x.status==="Template Missing"?"red":"grey"}>{x.status}</StatusBadge>{x.mandatory&&<span className="rounded bg-red-50 px-2 py-1 text-[10px] font-bold text-red-700">Mandatory</span>}</div><div className="mt-2 text-xs text-slate-500">{x.template_document||"No template located"}{x.approved_version&&" · approved v"+x.approved_version}</div></article>)}</div>
     <div className="hidden overflow-x-auto md:block"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{["Format","Kind","Priority","Mandatory","Template","Status","Approved Version"].map(h=><th key={h} className="px-4 py-3">{h}</th>)}</tr></thead><tbody>{data.formats.map(x=><tr key={x.requirement_id} className="border-t"><td className="px-4 py-3 font-semibold text-slate-900">{x.format_name}</td><td className="px-4 text-xs">{x.format_kind}</td><td className="px-4"><PriorityBadge value={x.priority}/></td><td className="px-4 text-xs">{x.mandatory?"Yes":"No"}</td><td className="max-w-xs px-4 text-xs"><div className="truncate">{x.template_document||"—"}</div></td><td className="px-4"><StatusBadge tone={x.status==="Approved"?"green":x.status==="Template Missing"?"red":"grey"}>{x.status}</StatusBadge></td><td className="px-4 text-xs">{x.approved_version?"v"+x.approved_version:"—"}</td></tr>)}</tbody></table></div>
    </>}
   </section>

   <section className="overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Approved Package Artifacts</h2><p className="text-xs text-slate-500">Only approved current versions are included in the controlled ZIP. The package contains a checksum manifest.</p></div>{data.approved_artifacts.length===0?<div className="p-4 text-sm text-slate-500">No approved artifacts are currently available for packaging.</div>:<div className="divide-y">{data.approved_artifacts.map(x=><div key={x.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><div className="truncate text-sm font-semibold text-slate-900">{x.artifact_name}</div><div className="mt-1 text-[11px] text-slate-500">{x.template_name||"Employer template"} · v{x.version_no} · {Math.round(x.file_size/1024)} KB</div></div><div className="font-mono text-[10px] text-slate-500">{x.checksum.slice(0,12)}…</div></div>)}</div>}</section>
  </>}
 </div>;
}
