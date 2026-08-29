"use client";

import Link from "next/link";
import {use,useCallback,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {EmptyState,ErrorState,LoadingState,PageHeader,StatusBadge,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,Document,P6ScheduleAnalysis,P6ScheduleComparison,Page} from "@/types";

const ISSUE_LABELS:Record<string,string>={
 open_start:"Open Start / No Predecessor",
 open_finish:"Open Finish / No Successor",
 negative_float:"Negative Total Float",
 zero_or_negative_float:"Zero / Negative Float",
 constraints:"Constraints",
 long_duration:"Long Duration",
 lagged_relationships:"Relationship Lags",
 dangling_relationships:"Dangling Relationships",
 status_date_issues:"Status / Actual Date Issues",
 missing_wbs:"Missing WBS",
 critical_float:"Critical by Total Float",
 near_critical_float:"Near-Critical by Total Float",
 milestones_at_risk:"Milestones at Risk",
};

export default function SchedulesPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [documents,setDocuments]=useState<Document[]>([]);
 const [selected,setSelected]=useState<number|null>(null);
 const [analysis,setAnalysis]=useState<P6ScheduleAnalysis|null>(null);
 const [baseline,setBaseline]=useState<number|null>(null);
 const [comparison,setComparison]=useState<P6ScheduleComparison|null>(null);
 const [comparing,setComparing]=useState(false);
 const [loading,setLoading]=useState(true);
 const [analyzing,setAnalyzing]=useState(false);
 const [error,setError]=useState("");

 const analyze=useCallback(async(documentId:number)=>{
  setAnalyzing(true);setError("");
  try{setAnalysis(await request<P6ScheduleAnalysis>("/documents/"+documentId+"/schedule-analysis"))}
  catch{setError("Unable to analyze this Primavera XER file.");setAnalysis(null)}
  finally{setAnalyzing(false)}
 },[]);

 const compareVersions=async()=>{
  if(!selected||!baseline||selected===baseline)return;
  setComparing(true);setError("");
  try{setComparison(await request<P6ScheduleComparison>("/documents/"+selected+"/schedule-comparison?baseline_document_id="+baseline))}
  catch{setError("Unable to compare these Primavera schedule versions.");setComparison(null)}
  finally{setComparing(false)}
 };

 useEffect(()=>{
  setLoading(true);setError("");
  Promise.all([
   request<Bid>("/bids/"+id),
   request<Page<Document>>("/bids/"+id+"/documents?extension=xer&page_size=100")
  ]).then(([b,d])=>{
   setBid(b);setDocuments(d.items);
   if(d.items.length){setSelected(d.items[0].id);analyze(d.items[0].id);if(d.items.length>1)setBaseline(d.items[1].id)}
  }).catch(()=>setError("Unable to load schedule documents.")).finally(()=>setLoading(false));
 },[id,analyze]);

 const issueEntries=analysis?Object.entries(analysis.issues).filter(([key,rows])=>key!=="zero_or_negative_float"&&rows.length>0):[];

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Schedules"/>
  <PageHeader items={[{label:"Bid Workspace",href:"/bids"},{label:"Schedules"}]} title="Primavera P6 Schedule Intelligence" description="Analyze uploaded XER schedules for structure, logic and schedule-health indicators before bid submission." action={<Link href={"/bids/"+id+"/documents"} className="rounded bg-[#304354] px-4 py-2 text-xs font-semibold text-white">Upload / Open Documents</Link>}/>

  {error&&<div className="mb-3"><ErrorState message={error}/></div>}
  {loading?<LoadingState label="Loading Primavera schedules…"/>:documents.length===0?<EmptyState title="No Primavera XER schedule uploaded" description="Upload the employer/bid schedule XER in Document Repository. The Schedules workspace will analyze it without changing the source file." action={<Link href={"/bids/"+id+"/documents"} className="rounded bg-[#e2b635] px-4 py-2 text-sm font-semibold text-[#243241]">Open Document Repository</Link>}/>:<>
   <section className="mb-3 flex flex-col gap-3 rounded border border-slate-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
    <div><div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Schedule File</div><select value={selected||""} onChange={e=>{const value=Number(e.target.value);setSelected(value);analyze(value)}} className="mt-1 min-w-[280px] max-w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800">{documents.map(d=><option key={d.id} value={d.id}>{d.document_title||d.original_filename}</option>)}</select></div>
    <div className="text-xs text-slate-500">{documents.length} XER file{documents.length===1?"":"s"} in this bid</div>
   </section>

   {documents.length>1&&<section className="mb-3 rounded border border-slate-200 bg-white p-3"><div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between"><div className="grid flex-1 gap-3 sm:grid-cols-2"><div><label className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Baseline / Earlier Version</label><select value={baseline||""} onChange={e=>{setBaseline(Number(e.target.value));setComparison(null)}} className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800"><option value="">Select baseline</option>{documents.filter(d=>d.id!==selected).map(d=><option key={d.id} value={d.id}>{d.document_title||d.original_filename}</option>)}</select></div><div><label className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Current / Later Version</label><div className="mt-1 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">{documents.find(d=>d.id===selected)?.document_title||documents.find(d=>d.id===selected)?.original_filename||"Current schedule"}</div></div></div><button disabled={!baseline||baseline===selected||comparing} onClick={compareVersions} className="rounded bg-[#304354] px-4 py-2 text-xs font-semibold text-white disabled:opacity-40">{comparing?"Comparing…":"Compare Versions"}</button></div><p className="mt-2 text-[11px] text-slate-500">Version comparison highlights schedule movement and logic changes; it does not by itself establish contractual delay responsibility or entitlement.</p></section>}

   {comparison&&<ScheduleComparisonPanel value={comparison}/>}
   {analyzing?<LoadingState label="Parsing XER and checking schedule health…"/>:analysis&&<>
    <section className={"mb-3 overflow-hidden rounded border "+(analysis.health.grade==="Good"?"border-emerald-200 bg-emerald-50":analysis.health.grade==="Needs Attention"?"border-amber-200 bg-amber-50":"border-red-200 bg-red-50")}><div className="grid gap-3 p-4 md:grid-cols-[150px_1fr]"><div><div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Health Screening</div><div className="mt-1 text-3xl font-bold text-slate-900">{Math.round(analysis.health.score)}%</div><div className="text-xs font-semibold text-slate-700">{analysis.health.grade}</div></div><div className="text-xs leading-5 text-slate-700"><div className="font-semibold text-slate-900">{analysis.project.project_name||analysis.project.project_code||"Primavera Project"}</div><div className="mt-1">{analysis.health.note}</div><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500"><span>Data date: {analysis.project.data_date?new Date(analysis.project.data_date).toLocaleString():"—"}</span><span>Planned start: {analysis.project.planned_start?new Date(analysis.project.planned_start).toLocaleDateString():"—"}</span><span>Planned finish: {analysis.project.planned_finish?new Date(analysis.project.planned_finish).toLocaleDateString():"—"}</span></div></div></div></section>

    <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-6">
     <SummaryCard label="Activities" value={analysis.counts.activities}/>
     <SummaryCard label="Relationships" value={analysis.counts.relationships}/>
     <SummaryCard label="WBS Nodes" value={analysis.counts.wbs_nodes}/>
     <SummaryCard label="Open Starts" value={analysis.health.issue_counts.open_start} tone="amber"/>
     <SummaryCard label="Open Finishes" value={analysis.health.issue_counts.open_finish} tone="amber"/>
     <SummaryCard label="Negative Float" value={analysis.health.issue_counts.negative_float} tone="red"/>
    </div>

    <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Schedule Parameter Inventory</h2><p className="text-xs text-slate-500">{analysis.optimization_advisor.parameter_inventory.note}</p></div><div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-4"><SummaryCard label="XER Tables" value={analysis.optimization_advisor.parameter_inventory.table_count}/><SummaryCard label="Unique Fields" value={analysis.optimization_advisor.parameter_inventory.total_fields}/><SummaryCard label="Total Rows" value={analysis.optimization_advisor.parameter_inventory.total_rows}/><SummaryCard label="Calendars" value={analysis.optimization_advisor.parameter_inventory.calendar_count}/></div><div className="max-h-[320px] overflow-auto border-t"><table className="w-full min-w-[700px] text-left text-xs"><thead className="sticky top-0 bg-white text-[10px] uppercase tracking-wide text-slate-500"><tr>{["Table","Rows","Fields","Sample Fields"].map(h=><th key={h} className="px-4 py-2">{h}</th>)}</tr></thead><tbody>{analysis.optimization_advisor.parameter_inventory.tables.map(x=><tr key={x.table} className="border-t"><td className="px-4 py-3 font-semibold text-slate-900">{x.table}</td><td className="px-4 py-3">{x.rows}</td><td className="px-4 py-3">{x.field_count}</td><td className="max-w-xl px-4 py-3 text-slate-500">{x.fields.slice(0,10).join(", ")}{x.fields.length>10?" …":""}</td></tr>)}</tbody></table></div></section>

    <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white"><div className="flex flex-col gap-2 border-b bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-sm font-bold text-slate-900">Schedule Optimization Advisor</h2><p className="text-xs text-slate-500">{analysis.optimization_advisor.optimization.note}</p></div><div className="flex flex-wrap gap-2 text-[10px] font-bold"><span className="rounded bg-red-50 px-2 py-1 text-red-700">{analysis.optimization_advisor.optimization.high_priority} HIGH</span><span className="rounded bg-amber-50 px-2 py-1 text-amber-700">{analysis.optimization_advisor.optimization.medium_priority} MEDIUM</span><span className="rounded bg-slate-100 px-2 py-1 text-slate-600">{analysis.optimization_advisor.optimization.low_priority} LOW</span></div></div><div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-4"><SummaryCard label="Candidates" value={analysis.optimization_advisor.optimization.candidate_count}/><SummaryCard label="High Priority" value={analysis.optimization_advisor.optimization.high_priority} tone="red"/><SummaryCard label="Medium Priority" value={analysis.optimization_advisor.optimization.medium_priority} tone="amber"/><SummaryCard label="Low Priority" value={analysis.optimization_advisor.optimization.low_priority}/></div>{analysis.optimization_advisor.optimization.candidates.length>0&&<div className="space-y-2 border-t p-3">{analysis.optimization_advisor.optimization.candidates.slice(0,60).map((x,i)=><article key={String(x.task_id||i)} className="rounded border border-slate-200 p-3"><div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><div className="text-[10px] font-bold uppercase tracking-wide text-blue-700">{String(x.task_code||"Activity")} · Score {x.adjustability_score}/100</div><div className="mt-1 text-sm font-semibold text-slate-900">{String(x.task_name||"Unnamed activity")}</div><div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500"><span>Float {x.total_float_hours} h</span><span>Duration {x.duration_hours} h</span><span>{x.predecessor_count} pred</span><span>{x.successor_count} succ</span><span>{x.resource_assignment_count} resource assignments</span></div></div><span className={x.priority==="High"?"rounded bg-red-50 px-2 py-1 text-[10px] font-bold text-red-700":x.priority==="Medium"?"rounded bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700":"rounded bg-slate-100 px-2 py-1 text-[10px] font-bold text-slate-600"}>{x.priority}</span></div>{x.issues.length>0&&<div className="mt-3 flex flex-wrap gap-1.5">{x.issues.map(issue=><span key={issue} className="rounded bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-700">{issue}</span>)}</div>}<div className="mt-3 space-y-1.5">{x.adjustment_opportunities.map((item,index)=><div key={index} className="rounded bg-blue-50/50 px-3 py-2 text-xs leading-5 text-slate-700">• {item}</div>)}</div><div className="mt-3 border-t pt-2 text-[10px] leading-4 text-slate-500">{x.guardrail}</div></article>)}</div>}</section>

    <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white"><div className="flex flex-col gap-2 border-b bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-sm font-bold text-slate-900">Float-Based Criticality Screening</h2><p className="text-xs text-slate-500">{analysis.criticality.note}</p></div><div className="text-[11px] font-semibold text-slate-500">Near-critical threshold: {analysis.criticality.near_critical_threshold_hours} h</div></div><div className="grid grid-cols-3 gap-2 p-3"><SummaryCard label="Critical" value={analysis.criticality.critical_activities.length} tone="red"/><SummaryCard label="Near-Critical" value={analysis.criticality.near_critical_activities.length} tone="amber"/><SummaryCard label="Milestones at Risk" value={analysis.criticality.milestones_at_risk.length} tone="amber"/></div>{analysis.criticality.milestones_at_risk.length>0&&<div className="border-t"><div className="divide-y">{analysis.criticality.milestones_at_risk.slice(0,20).map((x,i)=><div key={String(x.task_id||i)} className="grid gap-2 px-4 py-3 text-xs sm:grid-cols-[110px_1fr_auto]"><div className="font-semibold text-slate-900">{String(x.task_code||"—")}</div><div><div className="font-medium text-slate-800">{String(x.task_name||"Milestone")}</div><div className="mt-1 text-slate-500">{String(x.finish_date||"No finish date")}</div></div><div className="text-right"><div className={String(x.criticality)==="Critical"?"font-bold text-red-700":"font-bold text-amber-700"}>{String(x.criticality||"At Risk")}</div><div className="text-[10px] text-slate-500">{String(x.total_float_hours??"—")} h float</div></div></div>)}</div></div>}</section>

    <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white"><div className="flex flex-col gap-2 border-b bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-sm font-bold text-slate-900">Tender Schedule Alignment</h2><p className="text-xs text-slate-500">{analysis.tender_alignment.note}</p></div><StatusBadge tone={analysis.tender_alignment.grade==="Aligned"?"green":analysis.tender_alignment.grade==="Misaligned"?"red":"amber"}>{analysis.tender_alignment.grade}</StatusBadge></div><div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-5"><SummaryCard label="Schedule Requirements" value={analysis.tender_alignment.summary.schedule_requirements}/><SummaryCard label="Auto Checked" value={analysis.tender_alignment.summary.automatically_checked}/><SummaryCard label="Passed" value={analysis.tender_alignment.summary.passed} tone="green"/><SummaryCard label="Failed" value={analysis.tender_alignment.summary.failed} tone="red"/><SummaryCard label="Manual Review" value={analysis.tender_alignment.summary.manual_review} tone="amber"/></div>{analysis.tender_alignment.checks.length>0&&<div className="border-t"><div className="space-y-2 p-3 md:hidden">{analysis.tender_alignment.checks.map(x=><article key={x.requirement_id} className="rounded border border-slate-200 p-3"><div className="flex items-start justify-between gap-2"><div><div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{x.check_type}{x.source_clause&&" · Cl. "+x.source_clause}</div><div className="mt-1 text-sm font-semibold text-slate-900">{x.requirement_title}</div></div><StatusBadge tone={x.status==="Pass"?"green":x.status==="Fail"?"red":"amber"}>{x.status}</StatusBadge></div><div className="mt-2 grid grid-cols-2 gap-2 text-xs"><div><span className="text-slate-500">Expected</span><div className="font-medium text-slate-800">{x.expected||"—"}</div></div><div><span className="text-slate-500">Schedule</span><div className="font-medium text-slate-800">{x.actual||"—"}</div></div></div><div className="mt-2 text-xs leading-5 text-slate-600">{x.reason}</div></article>)}</div><div className="hidden overflow-x-auto md:block"><table className="w-full min-w-[1000px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr>{["Requirement","Check","Expected","Schedule","Status","Reason"].map(h=><th key={h} className="px-4 py-2">{h}</th>)}</tr></thead><tbody>{analysis.tender_alignment.checks.map(x=><tr key={x.requirement_id} className="border-t align-top"><td className="max-w-xs px-4 py-3"><div className="font-semibold text-slate-900">{x.requirement_title}</div>{x.source_clause&&<div className="text-[10px] text-slate-500">Cl. {x.source_clause}</div>}</td><td className="px-4 py-3">{x.check_type}</td><td className="px-4 py-3">{x.expected||"—"}</td><td className="max-w-xs px-4 py-3">{x.actual||"—"}</td><td className="px-4 py-3"><StatusBadge tone={x.status==="Pass"?"green":x.status==="Fail"?"red":"amber"}>{x.status}</StatusBadge></td><td className="max-w-sm px-4 py-3 text-slate-600">{x.reason}</td></tr>)}</tbody></table></div></div>}</section>

    <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Schedule Health Checks</h2><p className="text-xs text-slate-500">Deterministic screening of logic, float, constraints, duration and status/date consistency.</p></div><div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3 lg:grid-cols-5">{Object.entries(analysis.health.issue_counts).map(([key,value])=><div key={key} className="rounded border border-slate-200 p-3"><div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{ISSUE_LABELS[key]||key.replaceAll("_"," ")}</div><div className={"mt-1 text-xl font-bold "+(value>0?"text-amber-700":"text-emerald-700")}>{value}</div></div>)}</div></section>

    <section className="mb-3 grid gap-3 lg:grid-cols-3">
     <Distribution title="Activity Status" rows={analysis.distributions.activity_statuses}/>
     <Distribution title="Activity Type" rows={analysis.distributions.activity_types}/>
     <Distribution title="Relationship Type" rows={analysis.distributions.relationship_types}/>
    </section>

    {issueEntries.length>0&&<section className="space-y-3">{issueEntries.map(([key,rows])=><div key={key} className="overflow-hidden rounded border border-slate-200 bg-white"><div className="flex items-center justify-between border-b bg-slate-50 px-4 py-3"><div><h2 className="text-sm font-bold text-slate-900">{ISSUE_LABELS[key]||key.replaceAll("_"," ")}</h2><p className="text-xs text-slate-500">{rows.length} flagged item{rows.length===1?"":"s"}</p></div><StatusBadge tone={key==="negative_float"||key==="dangling_relationships"?"red":"amber"}>{rows.length}</StatusBadge></div><div className="max-h-[360px] overflow-auto"><div className="space-y-2 p-3 md:hidden">{rows.slice(0,100).map((x,index)=><IssueCard key={index} row={x}/>)}</div><div className="hidden md:block"><table className="w-full min-w-[800px] text-left text-xs"><thead className="sticky top-0 bg-white text-[10px] uppercase tracking-wide text-slate-500"><tr>{["Activity ID","Activity","Status","Detail"].map(h=><th key={h} className="px-4 py-2">{h}</th>)}</tr></thead><tbody>{rows.slice(0,100).map((x,index)=><tr key={index} className="border-t"><td className="px-4 py-3 font-semibold text-slate-800">{String(x.task_code||x.task_id||x.pred_task_id||"—")}</td><td className="max-w-sm px-4 py-3">{String(x.task_name||"—")}</td><td className="px-4 py-3">{String(x.status_code||"—")}</td><td className="max-w-md px-4 py-3 text-slate-500">{issueDetail(x)}</td></tr>)}</tbody></table></div></div></div>)}</section>}
   </>}
  </>}
 </div>;
}

function ScheduleComparisonPanel({value}:{value:P6ScheduleComparison}){
 const top=value.finish_slippage.slice(0,20);
 return <section className="mb-3 space-y-3">
  <div className="overflow-hidden rounded border border-slate-200 bg-white"><div className="flex items-start justify-between gap-3 border-b bg-slate-50 px-4 py-3"><div><h2 className="text-sm font-bold text-slate-900">Baseline / Update Comparison</h2><p className="text-xs text-slate-500">{value.note}</p></div><StatusBadge tone={value.risk_summary.risk_level==="High"?"red":value.risk_summary.risk_level==="Medium"?"amber":"green"}>{value.risk_summary.risk_level} Deterioration Risk</StatusBadge></div><div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-4 lg:grid-cols-8"><SummaryCard label="Added Activities" value={value.summary.added_activities} tone="amber"/><SummaryCard label="Deleted Activities" value={value.summary.deleted_activities} tone="amber"/><SummaryCard label="Finish Slippages" value={value.summary.finish_slippages} tone="red"/><SummaryCard label="Milestone Moves" value={value.summary.milestone_changes} tone="red"/><SummaryCard label="Duration Changes" value={value.summary.duration_changes}/><SummaryCard label="Float Changes" value={value.summary.float_changes}/><SummaryCard label="Added Logic" value={value.summary.added_relationships}/><SummaryCard label="Deleted Logic" value={value.summary.deleted_relationships}/><SummaryCard label="New Negative Float" value={value.summary.newly_negative_float} tone="red"/><SummaryCard label="Delayed Milestones" value={value.summary.delayed_milestones} tone="red"/></div><div className="border-t px-4 py-3 text-xs text-slate-600">Data date shift: <span className="font-semibold text-slate-800">{value.summary.data_date_shift_days??"—"} days</span> · Baseline: {value.baseline.data_date?new Date(value.baseline.data_date).toLocaleString():"—"} · Current: {value.current.data_date?new Date(value.current.data_date).toLocaleString():"—"}</div></div>
  <div className="rounded border border-slate-200 bg-white p-3 text-xs text-slate-600"><span className="font-semibold text-slate-800">Risk interpretation:</span> {value.risk_summary.note}</div>
  {value.milestone_changes.length>0&&<div className="overflow-hidden rounded border border-red-200 bg-white"><div className="border-b border-red-100 bg-red-50 px-4 py-3"><h3 className="text-sm font-bold text-red-800">Milestone Movement</h3></div><div className="divide-y">{value.milestone_changes.slice(0,20).map((x,i)=><div key={x.task_code||i} className="grid gap-2 px-4 py-3 text-xs sm:grid-cols-[120px_1fr_auto]"><div className="font-semibold text-slate-900">{x.task_code||"—"}</div><div><div className="font-medium text-slate-800">{x.task_name||"Milestone"}</div><div className="mt-1 text-slate-500">{x.baseline_finish?new Date(x.baseline_finish).toLocaleDateString():"—"} → {x.current_finish?new Date(x.current_finish).toLocaleDateString():"—"}</div></div><div className={(x.finish_variance_days||0)>0?"font-bold text-red-700":"font-bold text-emerald-700"}>{x.finish_variance_days??"—"} days</div></div>)}</div></div>}
  {top.length>0&&<div className="overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3"><h3 className="text-sm font-bold text-slate-900">Largest Finish Slippages</h3></div><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr>{["Activity","Name","Baseline Finish","Current Finish","Variance","Float Change"].map(h=><th key={h} className="px-4 py-2">{h}</th>)}</tr></thead><tbody>{top.map((x,i)=><tr key={x.task_code||i} className="border-t"><td className="px-4 py-3 font-semibold text-slate-900">{x.task_code||"—"}</td><td className="max-w-sm px-4 py-3">{x.task_name||"—"}</td><td className="px-4 py-3">{x.baseline_finish?new Date(x.baseline_finish).toLocaleDateString():"—"}</td><td className="px-4 py-3">{x.current_finish?new Date(x.current_finish).toLocaleDateString():"—"}</td><td className="px-4 py-3 font-bold text-red-700">{x.finish_variance_days??"—"} d</td><td className="px-4 py-3">{x.float_change_hours??"—"} h</td></tr>)}</tbody></table></div></div>}
 </section>
}

function Distribution({title,rows}:{title:string;rows:Array<{name:string;count:number}>}){
 return <div className="overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3 text-sm font-bold text-slate-900">{title}</div><div className="divide-y">{rows.slice(0,8).map(x=><div key={x.name} className="flex items-center justify-between px-4 py-2 text-xs"><span className="truncate text-slate-600">{x.name}</span><span className="font-bold text-slate-900">{x.count}</span></div>)}</div></div>
}

function IssueCard({row}:{row:Record<string,unknown>}){
 return <article className="rounded border border-slate-200 p-3"><div className="text-sm font-semibold text-slate-900">{String(row.task_code||row.task_id||row.pred_task_id||"Activity")}</div><div className="mt-1 text-xs text-slate-600">{String(row.task_name||"")}</div><div className="mt-2 text-[11px] text-slate-500">{issueDetail(row)}</div></article>
}

function issueDetail(row:Record<string,unknown>){
 const ignore=new Set(["task_id","task_code","task_name","status_code","task_type","wbs_id"]);
 return Object.entries(row).filter(([k,v])=>!ignore.has(k)&&v!==null&&v!==undefined&&v!=="").map(([k,v])=>k.replaceAll("_"," ")+": "+String(v)).join(" · ")||"Flagged by schedule-health rule.";
}
