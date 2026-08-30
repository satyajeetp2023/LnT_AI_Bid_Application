"use client";

import {use,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {ErrorState,LoadingState,PageHeader,StatusBadge,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,ClauseRiskFinding,ClauseRiskSummary,TenderQAResponse} from "@/types";

const dispositions=["Open","Escalate","Mitigated / Qualified","Accept Risk","Not Applicable","False Positive"];

export default function CopilotPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [risks,setRisks]=useState<ClauseRiskSummary|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");
 const [question,setQuestion]=useState("");
 const [asking,setAsking]=useState(false);
 const [answer,setAnswer]=useState<TenderQAResponse|null>(null);
 const [riskState,setRiskState]=useState<Record<number,{disposition:string;comment:string}>>({});

 const loadRisks=()=>request<ClauseRiskSummary>("/bids/"+id+"/clause-risks").then(setRisks);
 useEffect(()=>{
  setLoading(true);
  Promise.all([request<Bid>("/bids/"+id),request<ClauseRiskSummary>("/bids/"+id+"/clause-risks")])
   .then(([b,r])=>{setBid(b);setRisks(r)})
   .catch(()=>setError("Unable to load Bid Intelligence Copilot."))
   .finally(()=>setLoading(false));
 },[id]);

 const ask=async()=>{
  if(!question.trim())return;
  setAsking(true);setError("");
  try{setAnswer(await request<TenderQAResponse>("/bids/"+id+"/tender-qa",{method:"POST",body:JSON.stringify({question:question.trim()})}))}
  catch{setError("Unable to answer from tender evidence.")}
  finally{setAsking(false)}
 };

 const saveRisk=async(item:ClauseRiskFinding)=>{
  const state=riskState[item.id]||{disposition:item.reviewer_disposition||"Open",comment:item.reviewer_comment||""};
  try{
   await request("/clause-risks/"+item.id+"/review",{method:"POST",body:JSON.stringify(state)});
   await loadRisks();
  }catch{setError("Unable to save clause-risk review.")}
 };

 if(loading)return <div className="mx-auto max-w-[1500px]"><LoadingState label="Loading Bid Intelligence Copilot…"/></div>;

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Copilot"/>
  <PageHeader items={[{label:"Bid Workspace",href:"/bids"},{label:"Bid Intelligence Copilot"}]} title="Bid Intelligence Copilot" description="Ask grounded questions across this tender and review source-linked contractual risk flags. AI assists; the bid team decides."/>
  {error&&<div className="mb-3"><ErrorState message={error}/></div>}

  <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white">
   <div className="border-b bg-slate-50 px-4 py-3">
    <h2 className="text-sm font-bold text-slate-900">Ask This Tender</h2>
    <p className="text-xs text-slate-500">Answers are limited to this bid's indexed evidence and return source references. Weak evidence is reported as Not Found.</p>
   </div>
   <div className="p-4">
    <div className="flex flex-col gap-2 sm:flex-row">
     <input value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")ask()}} placeholder='Example: "What is the retention percentage?"' className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm"/>
     <button onClick={ask} disabled={asking||!question.trim()} className="rounded bg-[#304354] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{asking?"Checking tender…":"Ask Tender"}</button>
    </div>
    {answer&&<div className="mt-4 rounded border border-slate-200">
     <div className="flex flex-col gap-2 border-b bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm font-semibold text-slate-900">{answer.question}</div>
      <StatusBadge tone={answer.confidence==="Conflict"?"red":answer.grounded?(answer.confidence==="High"?"green":answer.confidence==="Medium"?"blue":"amber"):"grey"}>{answer.confidence}</StatusBadge>
     </div>
     <div className="p-4">
      <div className="text-sm leading-6 text-slate-800">{answer.answer}</div>{answer.conflicts.length>0&&<div className="mt-3 rounded border border-red-200 bg-red-50 p-3"><div className="text-[10px] font-bold uppercase tracking-wide text-red-700">Conflicting Tender Values</div><div className="mt-2 space-y-2">{answer.conflicts.map((group,i)=><div key={i}>{group.values.map((v,j)=><div key={j} className="text-xs text-red-800">• {v.display}{v.document_name?(" · "+v.document_name):""}{v.page?(" · p."+v.page):""}{v.clause?(" · Cl."+v.clause):""}</div>)}</div>)}</div><div className="mt-2 text-[10px] text-red-700">Do not rely on one value until the governing document/addendum is confirmed.</div></div>}
      <div className="mt-4 text-[10px] text-slate-500">{answer.note}</div>
      {answer.evidence.length>0&&<div className="mt-4 space-y-2">
       <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Source Evidence</div>
       {answer.evidence.map((e,i)=><div key={i} className="rounded border border-slate-200 bg-slate-50 p-3 text-xs">
        <div className="font-semibold text-slate-800">{e.document_name||"Tender evidence"}{e.page&&" · p."+e.page}{e.clause&&" · Cl."+e.clause}{e.section&&" · "+e.section}</div>
        <div className="mt-1 leading-5 text-slate-600">{e.excerpt}</div>
        <div className="mt-1 text-[10px] text-slate-400">{e.source_kind} · match {Math.round(e.score*100)}%</div>
       </div>)}
      </div>}
     </div>
    </div>}
   </div>
  </section>

  {risks&&<>
   <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
    <SummaryCard label="Risk Flags" value={risks.summary.total}/>
    <SummaryCard label="Open" value={risks.summary.open} tone="amber"/>
    <SummaryCard label="Critical" value={risks.summary.critical} tone="red"/>
    <SummaryCard label="High" value={risks.summary.high} tone="red"/>
    <SummaryCard label="Mitigated" value={risks.summary.mitigated} tone="green"/>
    <SummaryCard label="Accepted" value={risks.summary.accepted}/>
   </div>
   <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white">
    <div className="border-b bg-slate-50 px-4 py-3">
     <h2 className="text-sm font-bold text-slate-900">Clause Risk Radar</h2>
     <p className="text-xs text-slate-500">{risks.note}</p>
    </div>
    {risks.items.length===0?<div className="p-6 text-sm text-slate-500">No clause-risk findings have been detected yet.</div>:<div className="space-y-2 p-3">
     {risks.items.map(item=>{
      const state=riskState[item.id]||{disposition:item.reviewer_disposition||"Open",comment:item.reviewer_comment||""};
      return <article key={item.id} className={item.severity==="Critical"?"rounded border border-red-200 bg-red-50/30 p-3":"rounded border border-slate-200 bg-white p-3"}>
       <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
         <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{item.risk_category} · {item.risk_code}</div>
         <h3 className="mt-1 text-sm font-semibold text-slate-900">{item.risk_title}</h3>
         <div className="mt-1 text-[11px] text-slate-500">{item.source_document_name||"Tender document"}{item.source_page&&" · p."+item.source_page}{item.source_clause&&" · Cl."+item.source_clause}{item.source_section&&" · "+item.source_section}</div>
        </div>
        <StatusBadge tone={item.severity==="Critical"?"red":item.severity==="High"?"amber":"grey"}>{item.severity}</StatusBadge>
       </div>
       <div className="mt-3 rounded bg-slate-50 p-3 text-xs leading-5 text-slate-700"><span className="font-semibold">Source:</span> {item.source_excerpt}</div>
       {item.explanation&&<div className="mt-2 text-xs leading-5 text-slate-600"><span className="font-semibold text-slate-700">Why flagged:</span> {item.explanation}</div>}
       {item.reviewer_guidance&&<div className="mt-2 rounded bg-blue-50 p-3 text-xs leading-5 text-slate-700"><span className="font-semibold">Reviewer guidance:</span> {item.reviewer_guidance}</div>}
       <div className="mt-3 grid gap-2 lg:grid-cols-[220px_1fr_auto] lg:items-end">
        <div>
         <label className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Disposition</label>
         <select value={state.disposition} onChange={e=>setRiskState({...riskState,[item.id]:{...state,disposition:e.target.value}})} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-2 text-xs">{dispositions.map(x=><option key={x}>{x}</option>)}</select>
        </div>
        <div>
         <label className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Reviewer Comment</label>
         <input value={state.comment} onChange={e=>setRiskState({...riskState,[item.id]:{...state,comment:e.target.value}})} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-2 text-xs" placeholder="Qualification, mitigation, escalation note or false-positive reason"/>
        </div>
        <button onClick={()=>saveRisk(item)} className="rounded bg-[#304354] px-3 py-2 text-xs font-semibold text-white">Save Review</button>
       </div>
      </article>
     })}
    </div>}
   </section>
  </>}
 </div>
}
