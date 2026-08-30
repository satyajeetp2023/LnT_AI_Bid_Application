"use client";

import {useEffect,useState} from "react";
import {EmptyState,ErrorState,LoadingState,PageHeader,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {HistoricalBidIntelligence} from "@/types";

export default function HistoricalIntelligencePage(){
 const [data,setData]=useState<HistoricalBidIntelligence|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");
 const [projectType,setProjectType]=useState("");
 const [client,setClient]=useState("");
 const [projectTypes,setProjectTypes]=useState<string[]>([]);
 const [clients,setClients]=useState<string[]>([]);
 const [resultFrom,setResultFrom]=useState("");
 const [resultTo,setResultTo]=useState("");

 useEffect(()=>{
  setLoading(true);setError("");
  const params=new URLSearchParams();
  if(projectType)params.set("project_type",projectType);
  if(client)params.set("client",client);
  if(resultFrom)params.set("result_from",resultFrom);
  if(resultTo)params.set("result_to",resultTo);
  request<HistoricalBidIntelligence>("/historical-bids/intelligence"+(params.size?"?"+params.toString():""))
   .then(x=>{
    setData(x);
    if(!projectType&&!client){
     setProjectTypes(x.by_project_type.map(v=>v.name).filter(v=>v!=="Unspecified"));
     setClients(x.by_client.map(v=>v.name).filter(v=>v!=="Unspecified"));
    }
   }).catch(()=>setError("Unable to load historical bid intelligence."))
   .finally(()=>setLoading(false));
 },[projectType,client,resultFrom,resultTo]);

 if(loading)return <LoadingState label="Loading historical intelligence"/>;
 if(error)return <ErrorState message={error}/>;
 if(!data)return null;

 return <div className="mx-auto max-w-[1500px]">
  <PageHeader items={[{label:"Review & Insights"},{label:"Historical Intelligence"}]} title="Historical Bid Intelligence" description="Descriptive win/loss, competitor and market-spread intelligence from recorded tender results."/>
  <section className="mb-3 rounded border border-slate-200 bg-white p-3">
   <div className="flex flex-wrap items-end gap-3">
    <label className="min-w-52 text-xs font-semibold text-slate-600">Project Type<select value={projectType} onChange={e=>setProjectType(e.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2.5 py-2 text-xs font-normal text-slate-800"><option value="">All project types</option>{projectTypes.map(x=><option key={x}>{x}</option>)}</select></label>
    <label className="min-w-52 text-xs font-semibold text-slate-600">Client<select value={client} onChange={e=>setClient(e.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2.5 py-2 text-xs font-normal text-slate-800"><option value="">All clients</option>{clients.map(x=><option key={x}>{x}</option>)}</select></label>
    <label className="min-w-44 text-xs font-semibold text-slate-600">Result From<input type="date" value={resultFrom} onChange={e=>setResultFrom(e.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2.5 py-2 text-xs font-normal text-slate-800"/></label>
    <label className="min-w-44 text-xs font-semibold text-slate-600">Result To<input type="date" value={resultTo} onChange={e=>setResultTo(e.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2.5 py-2 text-xs font-normal text-slate-800"/></label>
    {(projectType||client||resultFrom||resultTo)&&<button onClick={()=>{setProjectType("");setClient("");setResultFrom("");setResultTo("")}} className="rounded border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700">Clear Filters</button>}
    <div className="text-[10px] text-slate-500">Filters apply server-side to historical bids you are authorized to view.</div>
   </div>
  </section>
  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
   <SummaryCard label="Recorded" value={data.summary.recorded}/>
   <SummaryCard label="Completed" value={data.summary.completed??0}/>
   <SummaryCard label="Won" value={data.summary.won} tone="green"/>
   <SummaryCard label="Lost" value={data.summary.lost} tone="red"/>
   <SummaryCard label="Win Rate" value={data.summary.win_rate_percent!==null?data.summary.win_rate_percent+"%":"—"}/>
   <SummaryCard label="Avg Rank" value={data.summary.average_our_rank??"—"}/>
   <SummaryCard label="Avg Gap to L1" value={data.summary.average_gap_to_l1_percent!==null&&data.summary.average_gap_to_l1_percent!==undefined?data.summary.average_gap_to_l1_percent+"%":"—"}/>
  </div>

  {data.summary.recorded===0?<EmptyState title="No historical results recorded yet" description="Bid Results will populate this page as tender outcomes are captured."/>:<>
   <section className="mb-3 rounded border border-slate-200 bg-white p-3">
    <div className="mb-3"><h2 className="text-sm font-bold text-slate-900">Historical Data Quality</h2><p className="text-xs text-slate-500">Coverage of source references and ranked-price evidence behind the historical intelligence.</p></div>
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
     <SummaryCard label="Completed Results" value={data.data_quality.completed_results}/>
     <SummaryCard label="Outcome Source Coverage" value={data.data_quality.outcome_source_coverage_percent!==null?data.data_quality.outcome_source_coverage_percent+"%":"—"}/>
     <SummaryCard label="Price Source Coverage" value={data.data_quality.price_source_coverage_percent!==null?data.data_quality.price_source_coverage_percent+"%":"—"}/>
     <SummaryCard label="Complete L1-L4" value={data.data_quality.complete_l1_l4_coverage_percent!==null?data.data_quality.complete_l1_l4_coverage_percent+"%":"—"}/>
     <SummaryCard label="Our Bid Identified" value={data.data_quality.results_with_our_bid_marked_percent!==null?data.data_quality.results_with_our_bid_marked_percent+"%":"—"}/>
    </div>
   </section>
   <section className="mb-3 rounded border border-slate-200 bg-white p-3">
    <div className="mb-3"><h2 className="text-sm font-bold text-slate-900">Recorded Market Price Spread</h2><p className="text-xs text-slate-500">Average premium of L2, L3 and L4 over L1 from completed tenders with ranked price evidence.</p></div>
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
     <SummaryCard label="Spread Samples" value={data.market_spread.samples}/>
     <SummaryCard label="Avg L2 vs L1" value={data.market_spread.average_l2_to_l1_percent!==null?data.market_spread.average_l2_to_l1_percent+"%":"—"}/>
     <SummaryCard label="Avg L3 vs L1" value={data.market_spread.average_l3_to_l1_percent!==null?data.market_spread.average_l3_to_l1_percent+"%":"—"}/>
     <SummaryCard label="Avg L4 vs L1" value={data.market_spread.average_l4_to_l1_percent!==null?data.market_spread.average_l4_to_l1_percent+"%":"—"}/>
    </div>
   </section>
   <div className="mb-3 grid gap-3 lg:grid-cols-2">
    <GroupTable title="Win Rate by Project Type" rows={data.by_project_type}/>
    <GroupTable title="Win Rate by Client" rows={data.by_client}/>
   </div>
   <section className="overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Competitor Presence</h2><p className="text-xs text-slate-500">Observed appearances and L1 positions from recorded bid results only.</p></div>{data.competitors.length===0?<div className="p-4 text-xs text-slate-500">No competitor rows recorded yet.</div>:<div className="overflow-x-auto"><table className="w-full min-w-[1120px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-2">Competitor</th><th className="px-4 py-2">Appearances</th><th className="px-4 py-2">L1 Wins</th><th className="px-4 py-2">L1 Rate</th><th className="px-4 py-2">Avg Rank</th><th className="px-4 py-2">Top Client</th><th className="px-4 py-2">Top Project Type</th><th className="px-4 py-2">Head to Head</th><th className="px-4 py-2">Competitor Ahead</th><th className="px-4 py-2">L&T Ahead</th></tr></thead><tbody>{data.competitors.map(x=><tr key={x.name} className="border-t"><td className="px-4 py-3 font-semibold text-slate-900">{x.name}</td><td className="px-4 py-3">{x.appearances}</td><td className="px-4 py-3">{x.l1_wins}</td><td className="px-4 py-3">{x.l1_rate_percent}%</td><td className="px-4 py-3">{x.average_rank}</td><td className="px-4 py-3">{x.top_client||"—"}</td><td className="px-4 py-3">{x.top_project_type||"—"}</td><td className="px-4 py-3">{x.head_to_head}</td><td className="px-4 py-3">{x.competitor_ahead}</td><td className="px-4 py-3">{x.our_ahead}</td></tr>)}</tbody></table></div>}</section>
  </>}
  <div className="mt-3 text-[10px] text-slate-500">{data.note}</div>
 </div>;
}

function GroupTable({title,rows}:{title:string;rows:Array<{name:string;bids:number;won:number;win_rate_percent:number}>}){
 return <section className="overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3 text-sm font-bold text-slate-900">{title}</div>{rows.length===0?<div className="p-4 text-xs text-slate-500">No completed result data.</div>:<div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-2">Group</th><th className="px-4 py-2">Bids</th><th className="px-4 py-2">Won</th><th className="px-4 py-2">Win Rate</th></tr></thead><tbody>{rows.map(x=><tr key={x.name} className="border-t"><td className="px-4 py-3 font-semibold text-slate-900">{x.name}</td><td className="px-4 py-3">{x.bids}</td><td className="px-4 py-3">{x.won}</td><td className="px-4 py-3">{x.win_rate_percent}%</td></tr>)}</tbody></table></div>}</section>
}
