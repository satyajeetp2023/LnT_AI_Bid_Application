"use client";

import {use,useEffect,useState} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {ErrorState,LoadingState,PageHeader,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,BidDecisionAnalytics} from "@/types";

export default function DecisionAnalyticsPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [data,setData]=useState<BidDecisionAnalytics|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");

 useEffect(()=>{
  setLoading(true);setError("");
  Promise.all([request<Bid>("/bids/"+id),request<BidDecisionAnalytics>("/bids/"+id+"/decision-analytics")])
   .then(([b,d])=>{setBid(b);setData(d)})
   .catch(e=>setError(e instanceof Error?e.message:"Unable to load decision analytics."))
   .finally(()=>setLoading(false));
 },[id]);

 if(loading)return <LoadingState label="Loading decision analytics"/>;
 if(error)return <ErrorState message={error}/>;
 if(!data)return null;
 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Decision Analytics"/>
  <PageHeader items={[{label:"Bid Workspace",href:"/bids"},{label:"Decision Analytics"}]} title="Management Bid Decision Analytics" description="Explainable evidence-weighted readiness for management review. This module does not autonomously decide whether to bid and does not predict win probability."/>
  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-5">
   <SummaryCard label="Decision Posture" value={data.decision_posture}/>
   <SummaryCard label="Readiness Score" value={data.readiness_score+"%"}/>
   <SummaryCard label="Hard Blockers" value={data.hard_blockers.length}/>
   <SummaryCard label="Historical Comparables" value={data.historical_context.summary.comparable_bids}/>
   <SummaryCard label="Evidence Confidence" value={data.confidence.level}/>
  </div>

  <section className="mb-3 rounded border border-slate-200 bg-white p-3">
   <div className="mb-3"><h2 className="text-sm font-bold text-slate-900">Decision Readiness Dimensions</h2><p className="text-xs text-slate-500">Each dimension uses visible deterministic rules and shows every deduction.</p></div>
   <div className="grid gap-3 lg:grid-cols-5">{data.dimensions.map(x=><div key={x.name} className="rounded border border-slate-200 p-3"><div className="text-xs font-bold text-slate-900">{x.name}</div><div className="mt-1 text-2xl font-bold text-[#304354]">{x.score}%</div><div className="text-[10px] text-slate-500">Weight {x.weight}% · weighted {x.weighted_score}</div>{x.penalties.length>0?<div className="mt-3 space-y-2">{x.penalties.map(p=><div key={p.code} className="rounded bg-amber-50 p-2 text-[10px] text-amber-900"><div className="font-semibold">-{p.points} pts</div><div>{p.message}</div></div>)}</div>:<div className="mt-3 rounded bg-emerald-50 p-2 text-[10px] text-emerald-800">{x.passes[0]||"No penalty."}</div>}</div>)}</div>
  </section>

  <div className="mb-3 grid gap-3 lg:grid-cols-2">
   <section className="rounded border border-slate-200 bg-white p-3"><h2 className="text-sm font-bold text-slate-900">Hard Blockers</h2>{data.hard_blockers.length===0?<div className="mt-3 text-xs text-emerald-700">No hard blocker is currently identified by the deterministic rules.</div>:<ul className="mt-3 list-disc space-y-2 pl-5 text-xs text-red-800">{data.hard_blockers.map((x,i)=><li key={i}>{x}</li>)}</ul>}</section>
   <section className="rounded border border-slate-200 bg-white p-3"><h2 className="text-sm font-bold text-slate-900">Confidence Limits</h2>{data.confidence.reasons.length===0?<div className="mt-3 text-xs text-emerald-700">No current evidence-confidence limitation is flagged.</div>:<ul className="mt-3 list-disc space-y-2 pl-5 text-xs text-slate-700">{data.confidence.reasons.map((x,i)=><li key={i}>{x}</li>)}</ul>}</section>
  </div>

  <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white">
   <div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">Comparable Historical Bids</h2><p className="text-xs text-slate-500">Descriptive context only. Similarity does not imply future win probability.</p></div>
   {data.historical_context.matches.length===0?<div className="p-4 text-xs text-slate-500">No comparable completed bids are available yet.</div>:<div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-2">Bid</th><th className="px-4 py-2">Client</th><th className="px-4 py-2">Type</th><th className="px-4 py-2">Result</th><th className="px-4 py-2">Our Rank</th><th className="px-4 py-2">Gap to L1</th><th className="px-4 py-2">Similarity</th></tr></thead><tbody>{data.historical_context.matches.map(x=><tr key={x.bid_project_id} className="border-t"><td className="px-4 py-3">{x.bid_id}</td><td className="px-4 py-3">{x.client}</td><td className="px-4 py-3">{x.project_type}</td><td className="px-4 py-3">{x.result_status}</td><td className="px-4 py-3">{x.our_rank??"—"}</td><td className="px-4 py-3">{x.our_gap_to_l1_percent!==null?x.our_gap_to_l1_percent+"%":"—"}</td><td className="px-4 py-3 font-semibold">{x.similarity_score}%</td></tr>)}</tbody></table></div>}
  </section>

  <section className="mb-3 rounded border border-slate-200 bg-white p-3">
   <div className="mb-3"><h2 className="text-sm font-bold text-slate-900">Reviewed Execution Lessons from Similar Bids</h2><p className="text-xs text-slate-500">Only reviewed, source-backed lessons from bids with at least 50% deterministic similarity are shown.</p></div>
   {data.reviewed_execution_lessons.length===0?<div className="text-xs text-slate-500">No reviewed execution lesson is available from sufficiently similar bids.</div>:<div className="space-y-2">{data.reviewed_execution_lessons.map((x,i)=><div key={i} className="rounded border border-slate-200 p-3 text-xs"><div className="font-semibold text-slate-900">{x.title}</div><div className="mt-1 text-[10px] text-slate-500">{x.category} · {x.impact_area} · {x.direction}</div><div className="mt-2 text-slate-700">{x.lesson_for_future_bids}</div><div className="mt-2 text-[10px] text-slate-500">Source: {x.source_reference||"—"}</div></div>)}</div>}
  </section>

  <section className="rounded border border-slate-200 bg-slate-50 p-3 text-[10px] text-slate-600"><div className="font-semibold text-slate-800">{data.methodology.type}</div><div className="mt-1">{data.methodology.hard_blocker_rule}</div><div className="mt-1">{data.note}</div></section>
 </div>;
}
