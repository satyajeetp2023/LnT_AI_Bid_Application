"use client";

import Link from "next/link";
import {use,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {EmptyState,ErrorState,LoadingState,PageHeader,PriorityBadge,SourceEvidenceCard,SummaryCard} from "@/components/design-system";
import {API,request} from "@/services/api";
import type {Bid,SubmissionFormatCandidateResponse,TemplatePopulationPlan} from "@/types";

const empty:SubmissionFormatCandidateResponse={items:[],summary:{detected:0,mandatory:0,high_priority:0,with_source:0,template_located:0,template_missing:0},version:""};

export default function BidPreparationPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [data,setData]=useState<SubmissionFormatCandidateResponse>(empty);
 const [loading,setLoading]=useState(true);
 const [plan,setPlan]=useState<TemplatePopulationPlan|null>(null);
 const [selectedTemplateId,setSelectedTemplateId]=useState<number|null>(null);
 const [choiceMark,setChoiceMark]=useState("X");
 const [headerValues,setHeaderValues]=useState<Record<string,string>>({});
 const [fieldOverrides,setFieldOverrides]=useState<Record<string,string>>({});
 const [generating,setGenerating]=useState(false);
 const [planLoading,setPlanLoading]=useState(false);
 const [planError,setPlanError]=useState("");
 const [error,setError]=useState("");
 const inspectTemplate=async(documentId:number)=>{
  setPlanLoading(true);setPlanError("");
  try{const nextPlan=await request<TemplatePopulationPlan>(`/documents/${documentId}/population-plan`);setPlan(nextPlan);setSelectedTemplateId(documentId);setHeaderValues(Object.fromEntries(nextPlan.header_inputs.map(x=>[x.semantic_field,""])));setFieldOverrides({}))}
  catch{setPlanError("Unable to build a population plan for this template.")}
  finally{setPlanLoading(false)}
 };
 const generateDraft=async()=>{
  if(!selectedTemplateId)return;
  setGenerating(true);setPlanError("");
  try{
   const q=new URLSearchParams({choice_mark:choiceMark});
   const r=await fetch(`${API}/documents/${selectedTemplateId}/generate-controlled-draft?${q.toString()}`,{method:"POST",headers:{"X-User-ID":"1","Content-Type":"application/json"},body:JSON.stringify({header_values:headerValues,field_overrides:fieldOverrides})});
   if(!r.ok){const e=await r.json().catch(()=>({detail:"Draft generation failed"}));throw new Error(e.detail||"Draft generation failed")}
   const blob=await r.blob();
   const disposition=r.headers.get("content-disposition")||"";
   const match=disposition.match(/filename="?([^";]+)"?/i);
   const filename=match?.[1]||"controlled_draft.xlsx";
   const url=URL.createObjectURL(blob);
   const a=document.createElement("a");a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
  }catch{setPlanError("Unable to generate the controlled draft.")}
  finally{setGenerating(false)}
 };
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
  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-6">
   <SummaryCard label="Detected Formats" value={data.summary.detected}/>
   <SummaryCard label="Mandatory" value={data.summary.mandatory} tone="red"/>
   <SummaryCard label="High Priority" value={data.summary.high_priority} tone="amber"/>
   <SummaryCard label="With Source Traceability" value={data.summary.with_source} tone="green"/>
   <SummaryCard label="Templates Located" value={data.summary.template_located} tone="green"/>
   <SummaryCard label="Templates Missing" value={data.summary.template_missing} tone="amber"/>
  </div>
  {error?<ErrorState message={error}/>:loading?<LoadingState label="Scanning extracted requirements for employer-prescribed formats…"/>:data.items.length===0?<EmptyState title="No prescribed submission formats detected yet" description="Formats will appear here automatically when extracted tender requirements refer to forms, annexures, schedules, appendices or prescribed templates."/>:<section className="grid gap-3 lg:grid-cols-2">
   {data.items.map(x=><article key={`${x.requirement_id}-${x.format_name}`} className="rounded border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="text-[10px] font-bold uppercase tracking-wide text-blue-700">{x.format_kind}</div><h2 className="mt-0.5 text-sm font-semibold text-slate-900">{x.format_name}</h2></div><PriorityBadge value={x.priority}/></div>
    <div className="mt-2 text-xs leading-5 text-slate-600">{x.requirement_text}</div>
    <div className="mt-3 flex flex-wrap gap-2 text-[11px]"><span className={x.status==="Template Located"?"rounded bg-emerald-50 px-2 py-1 font-semibold text-emerald-700":"rounded bg-amber-50 px-2 py-1 font-semibold text-amber-700"}>{x.status}</span>{x.mandatory&&<span className="rounded bg-red-50 px-2 py-1 font-semibold text-red-700">Mandatory</span>}<span className="rounded bg-blue-50 px-2 py-1 font-semibold text-blue-700">{Math.round(x.confidence*100)}% detection confidence</span>{x.template_document&&<span className="rounded bg-slate-100 px-2 py-1 font-semibold text-slate-700">{Math.round(x.template_match_confidence*100)}% template match</span>}</div>
    <div className="mt-3 rounded bg-slate-50 p-2 text-xs leading-5 text-slate-600"><span className="font-semibold text-slate-700">Next:</span> {x.next_action}{x.template_document&&<div className="mt-1"><span className="font-semibold text-slate-700">Matched template:</span> {x.template_document}</div>}</div>
    <div className="mt-3"><SourceEvidenceCard document={x.source_document||"No source document"} page={x.source_page} clause={x.source_clause} section={x.source_section} excerpt={x.source_excerpt}/></div>
    <div className="mt-3 flex flex-wrap gap-2 border-t pt-3"><Link href={`/bids/${id}/requirements`} className="rounded border border-slate-300 px-3 py-2 text-xs font-semibold text-blue-700">Open Requirement</Link>{x.source_document_id&&<Link href={`/bids/${id}/documents`} className="rounded border border-slate-300 px-3 py-2 text-xs font-semibold text-blue-700">Open Documents</Link>}{x.template_document_id&&x.template_extension==="xlsx"&&<button onClick={()=>inspectTemplate(x.template_document_id!)} className="rounded bg-[#e2b635] px-3 py-2 text-xs font-semibold text-[#243241]">Inspect Population Plan</button>}</div>
   </article>)}
  </section>}
  {planLoading&&<div className="mt-3"><LoadingState label="Building controlled population plan…"/></div>}
  {planError&&<div className="mt-3"><ErrorState message={planError}/></div>}
  {plan&&<section className="mt-3 overflow-hidden rounded border border-slate-200 bg-white">
   <div className="flex flex-col gap-3 border-b bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-sm font-bold text-slate-900">Template Population Plan</h2><p className="text-xs text-slate-500">Clause-by-clause mapping between the employer template and reviewed tender requirements. The original employer file remains untouched.</p></div><div className="flex flex-wrap items-center gap-2"><label className="text-xs font-semibold text-slate-600">Compliance mark</label><select value={choiceMark} onChange={e=>setChoiceMark(e.target.value)} className="rounded border border-slate-300 bg-white px-2.5 py-2 text-xs font-semibold text-slate-700"><option value="X">X</option><option value="✓">✓</option></select><button disabled={!selectedTemplateId||generating} onClick={generateDraft} className="rounded bg-[#304354] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{generating?"Generating…":"Generate Controlled Draft"}</button></div></div>
   {plan.header_inputs.length>0&&<div className="border-b bg-amber-50/50 p-3"><div className="mb-2"><h3 className="text-xs font-bold text-slate-900">Workbook Header Inputs</h3><p className="text-[11px] text-slate-600">Enter each value once. The controlled draft will propagate it to every repeated employer placeholder.</p></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{plan.header_inputs.map(x=><div key={x.semantic_field}><label className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{x.label}</label><input value={headerValues[x.semantic_field]||""} onChange={e=>setHeaderValues({...headerValues,[x.semantic_field]:e.target.value})} placeholder={x.semantic_field==="tenderer_name"?"Tenderer / bidder name":"Enter value"} className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800"/><div className="mt-1 text-[10px] text-slate-500">Repeated {x.occurrence_count} time{x.occurrence_count===1?"":"s"} · {x.input_source.replaceAll("_"," ")}</div></div>)}</div></div>}<div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3 lg:grid-cols-6">
    <SummaryCard label="Template Rows" value={plan.summary.template_rows}/>
    <SummaryCard label="Matched" value={plan.summary.requirements_matched} tone="green"/>
    <SummaryCard label="Unmatched" value={plan.summary.unmatched_rows} tone="amber"/>
    <SummaryCard label="Rows Need Action" value={plan.summary.rows_requiring_action} tone="amber"/>
    <SummaryCard label="Safe Autofill Fields" value={plan.summary.safe_auto_fill_fields} tone="green"/>
    <SummaryCard label="Suggested Text" value={plan.summary.suggested_text_fields}/>
   </div>
   <div className="max-h-[650px] overflow-auto border-t">
    <table className="w-full min-w-[1100px] text-left text-xs">
     <thead className="sticky top-0 bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr>{["Sheet","Clause","Matched Requirement","Compliance","Match","Population Actions"].map(h=><th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
     <tbody>{plan.rows.map(row=><tr key={`${row.sheet}-${row.clause_reference}`} className="border-t align-top">
      <td className="px-3 py-3 font-semibold text-slate-700">{row.sheet}</td>
      <td className="px-3 py-3 font-semibold text-slate-900">{row.clause_reference||"—"}</td>
      <td className="max-w-xs px-3 py-3"><div className="line-clamp-3">{row.requirement_title||<span className="font-semibold text-amber-700">No unique match</span>}</div></td>
      <td className="px-3 py-3">{row.compliance_status||"—"}{row.requirement_review_status&&<div className="mt-1 text-[10px] text-slate-500">{row.requirement_review_status}</div>}</td>
      <td className="px-3 py-3">{Math.round(row.match_confidence*100)}%</td>
      <td className="px-3 py-3"><div className="space-y-1.5">{row.fields.filter(f=>f.action!=="preserve").map(f=>{const key=`${row.sheet}!${f.coordinate}`;const editable=f.ownership!=="employer_only"&&["needs_review","needs_human_decision","needs_assessment","needs_input","suggest_text","leave_blank"].includes(f.action);const binary=f.semantic_field==="compliant_yes"||f.semantic_field==="compliant_no";return <div key={`${f.coordinate}-${f.semantic_field}`} className="rounded bg-slate-50 p-2"><div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-slate-700">{f.coordinate||"—"} · {f.header||f.semantic_field}</span><span className={f.action==="propose_auto_fill"?"rounded bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-700":f.action==="employer_only"?"rounded bg-slate-200 px-1.5 py-0.5 text-[9px] font-bold text-slate-600":"rounded bg-amber-50 px-1.5 py-0.5 text-[9px] font-bold text-amber-700"}>{f.action.replaceAll("_"," ")}</span></div>{f.proposed_value!==null&&f.proposed_value!==""&&<div className="mt-1 font-medium text-slate-800">Proposed: {f.proposed_value}</div>}{editable&&(binary?<label className="mt-2 flex items-center gap-2 text-[10px] font-semibold text-slate-700"><input type="checkbox" checked={!!fieldOverrides[key]} onChange={e=>{const next={...fieldOverrides};for(const candidate of row.fields.filter(x=>x.semantic_field==="compliant_yes"||x.semantic_field==="compliant_no"))delete next[`${row.sheet}!${candidate.coordinate}`];if(e.target.checked)next[key]=choiceMark;setFieldOverrides(next)}}/>Select this compliance option</label>:<textarea rows={2} value={fieldOverrides[key]||""} onChange={e=>setFieldOverrides({...fieldOverrides,[key]:e.target.value})} placeholder="Bidder input / override" className="mt-2 w-full rounded border border-slate-300 bg-white p-2 text-[11px] text-slate-800"/>)}{f.reason&&<div className="mt-1 text-[10px] leading-4 text-slate-500">{f.reason}</div>}</div>})}</div></td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>}
 </div>;
}
