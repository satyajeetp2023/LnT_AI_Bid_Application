"use client";

import {useEffect,useState} from "react";
import {EmptyState,ErrorState,LoadingState,PageHeader,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {ExecutionLearningIntelligence} from "@/types";

export default function ExecutionLearningPortfolioPage(){
 const [data,setData]=useState<ExecutionLearningIntelligence|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");

 useEffect(()=>{
  request<ExecutionLearningIntelligence>("/execution-learning/intelligence")
   .then(setData).catch(e=>setError(e instanceof Error?e.message:"Unable to load execution learning."))
   .finally(()=>setLoading(false));
 },[]);

 if(loading)return <LoadingState label="Loading execution learning"/>;
 if(error)return <ErrorState message={error}/>;
 if(!data)return null;

 return <div className="mx-auto max-w-[1500px]">
  <PageHeader items={[{label:"Review & Insights"},{label:"Execution Learning"}]} title="Bid vs Actual Execution Learning" description="Portfolio learning from reviewed execution actuals only. Missing project actuals remain unknown and are not inferred."/>
  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-5">
   <SummaryCard label="Reviewed Projects" value={data.summary.reviewed_projects}/>
   <SummaryCard label="Avg Revenue Change vs Bid" value={data.summary.average_revenue_change_vs_bid_percent!==null&&data.summary.average_revenue_change_vs_bid_percent!==undefined?data.summary.average_revenue_change_vs_bid_percent+"%":"—"}/>
   <SummaryCard label="Avg Margin Change" value={data.summary.average_margin_change_percentage_points!==null&&data.summary.average_margin_change_percentage_points!==undefined?data.summary.average_margin_change_percentage_points+" pp":"—"}/>
   <SummaryCard label="Avg Actual Duration" value={data.summary.average_actual_duration_days!==null&&data.summary.average_actual_duration_days!==undefined?data.summary.average_actual_duration_days+" days":"—"}/>
   <SummaryCard label="Avg EOT" value={data.summary.average_eot_days!==null&&data.summary.average_eot_days!==undefined?data.summary.average_eot_days+" days":"—"}/>
  </div>
  {data.records.length===0?<EmptyState title="No reviewed execution actuals yet" description="Won bids appear here only after execution actuals have evidence and are marked Reviewed."/>:
  <section className="overflow-hidden rounded border border-slate-200 bg-white">
   <div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Reviewed Project Learning Register</h2><p className="text-xs text-slate-500">Each row links back to the bid workspace and uses only reviewed execution evidence.</p></div>
   <div className="overflow-x-auto"><table className="w-full min-w-[1100px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-2">Bid</th><th className="px-4 py-2">Client</th><th className="px-4 py-2">Project Type</th><th className="px-4 py-2">Execution Status</th><th className="px-4 py-2">Revenue Change</th><th className="px-4 py-2">Margin Change</th><th className="px-4 py-2">Actual Duration</th><th className="px-4 py-2">EOT</th><th className="px-4 py-2">Source</th></tr></thead><tbody>{data.records.map(x=><tr key={x.bid_project_id} className="border-t"><td className="px-4 py-3"><a href={"/bids/"+x.bid_project_id+"/execution-learning"} className="font-semibold text-[#304354] underline-offset-2 hover:underline">{x.bid_id}</a><div className="max-w-64 truncate text-[10px] text-slate-500">{x.tender_name||"—"}</div></td><td className="px-4 py-3">{x.client||"—"}</td><td className="px-4 py-3">{x.project_type||"—"}</td><td className="px-4 py-3">{x.execution.execution_status}</td><td className="px-4 py-3">{x.comparison.revenue_change_vs_bid_percent!==null?x.comparison.revenue_change_vs_bid_percent+"%":"—"}</td><td className="px-4 py-3">{x.comparison.margin_change_percentage_points!==null?x.comparison.margin_change_percentage_points+" pp":"—"}</td><td className="px-4 py-3">{x.comparison.actual_duration_days!==null?x.comparison.actual_duration_days+" days":"—"}</td><td className="px-4 py-3">{x.execution.eot_days!==null?x.execution.eot_days+" days":"—"}</td><td className="px-4 py-3">{x.execution.source_reference||"—"}</td></tr>)}</tbody></table></div>
  </section>}
  <div className="mt-3 text-[10px] text-slate-500">{data.note}</div>
 </div>;
}
