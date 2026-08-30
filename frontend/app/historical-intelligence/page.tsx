"use client";

import {useEffect,useState} from "react";
import {EmptyState,ErrorState,LoadingState,PageHeader,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {HistoricalBidIntelligence} from "@/types";

export default function HistoricalIntelligencePage(){
 const [data,setData]=useState<HistoricalBidIntelligence|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");

 useEffect(()=>{
  request<HistoricalBidIntelligence>("/historical-bids/intelligence")
   .then(setData).catch(()=>setError("Unable to load historical bid intelligence."))
   .finally(()=>setLoading(false));
 },[]);

 if(loading)return <LoadingState label="Loading historical intelligence"/>;
 if(error)return <ErrorState message={error}/>;
 if(!data)return null;

 return <div className="mx-auto max-w-[1500px]">
  <PageHeader items={[{label:"Review & Insights"},{label:"Historical Intelligence"}]} title="Historical Bid Intelligence" description="Descriptive win/loss and competitor intelligence from recorded tender results."/>
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
   <div className="mb-3 grid gap-3 lg:grid-cols-2">
    <GroupTable title="Win Rate by Project Type" rows={data.by_project_type}/>
    <GroupTable title="Win Rate by Client" rows={data.by_client}/>
   </div>
   <section className="overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Competitor Presence</h2><p className="text-xs text-slate-500">Observed appearances and L1 positions from recorded bid results only.</p></div>{data.competitors.length===0?<div className="p-4 text-xs text-slate-500">No competitor rows recorded yet.</div>:<div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-2">Competitor</th><th className="px-4 py-2">Appearances</th><th className="px-4 py-2">L1 Wins</th></tr></thead><tbody>{data.competitors.map(x=><tr key={x.name} className="border-t"><td className="px-4 py-3 font-semibold text-slate-900">{x.name}</td><td className="px-4 py-3">{x.appearances}</td><td className="px-4 py-3">{x.l1_wins}</td></tr>)}</tbody></table></div>}</section>
  </>}
  <div className="mt-3 text-[10px] text-slate-500">{data.note}</div>
 </div>;
}

function GroupTable({title,rows}:{title:string;rows:Array<{name:string;bids:number;won:number;win_rate_percent:number}>}){
 return <section className="overflow-hidden rounded border border-slate-200 bg-white"><div className="border-b bg-slate-50 px-4 py-3 text-sm font-bold text-slate-900">{title}</div>{rows.length===0?<div className="p-4 text-xs text-slate-500">No completed result data.</div>:<div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-2">Group</th><th className="px-4 py-2">Bids</th><th className="px-4 py-2">Won</th><th className="px-4 py-2">Win Rate</th></tr></thead><tbody>{rows.map(x=><tr key={x.name} className="border-t"><td className="px-4 py-3 font-semibold text-slate-900">{x.name}</td><td className="px-4 py-3">{x.bids}</td><td className="px-4 py-3">{x.won}</td><td className="px-4 py-3">{x.win_rate_percent}%</td></tr>)}</tbody></table></div>}</section>
}
