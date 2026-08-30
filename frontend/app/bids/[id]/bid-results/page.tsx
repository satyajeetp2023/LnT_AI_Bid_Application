"use client";

import {use,useEffect,useState,type ReactNode} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {ErrorState,LoadingState,PageHeader,StatusBadge,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,BidOutcomeResponse,HistoricalBidPrice} from "@/types";

const emptyPrice=(rank:number):HistoricalBidPrice=>({rank,bidder_name:"",bid_value:0,currency:"INR",is_ours:false,source_reference:null});
const inputClass="w-full rounded border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-800 outline-none focus:border-[#c69b2d] focus:ring-2 focus:ring-[#d5aa35]/20";

export default function BidResultsPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [result,setResult]=useState<BidOutcomeResponse|null>(null);
 const [loading,setLoading]=useState(true);
 const [saving,setSaving]=useState(false);
 const [error,setError]=useState("");
 const [status,setStatus]=useState("Result Awaited");
 const [resultDate,setResultDate]=useState("");
 const [ourRank,setOurRank]=useState("");
 const [ourBidValue,setOurBidValue]=useState("");
 const [margin,setMargin]=useState("");
 const [awardedBidder,setAwardedBidder]=useState("");
 const [sourceReference,setSourceReference]=useState("");
 const [reason,setReason]=useState("");
 const [notes,setNotes]=useState("");
 const [prices,setPrices]=useState<HistoricalBidPrice[]>([1,2,3,4].map(emptyPrice));

 const apply=(x:BidOutcomeResponse)=>{
  setResult(x);
  const o=x.outcome;
  setStatus(o?.result_status||"Result Awaited");
  setResultDate(o?.result_date||"");
  setOurRank(o?.our_rank?String(o.our_rank):"");
  setOurBidValue(o?.our_bid_value!==null&&o?.our_bid_value!==undefined?String(o.our_bid_value):"");
  setMargin(o?.our_margin_percent!==null&&o?.our_margin_percent!==undefined?String(o.our_margin_percent):"");
  setAwardedBidder(o?.awarded_bidder||"");
  setSourceReference(o?.source_reference||"");
  setReason(o?.result_status==="Won"?(o.win_reason||""):(o?.loss_reason||""));
  setNotes(o?.notes||"");
  const byRank=new Map(x.prices.map(p=>[p.rank,p]));
  setPrices([1,2,3,4].map(rank=>byRank.get(rank)||emptyPrice(rank)));
 };

 useEffect(()=>{
  setLoading(true);setError("");
  Promise.all([request<Bid>("/bids/"+id),request<BidOutcomeResponse>("/bids/"+id+"/outcome")])
   .then(([b,o])=>{setBid(b);apply(o)})
   .catch(()=>setError("Unable to load bid result information."))
   .finally(()=>setLoading(false));
 },[id]);

 const updatePrice=(rank:number,patch:Partial<HistoricalBidPrice>)=>{
  setPrices(rows=>rows.map(x=>x.rank===rank?{...x,...patch}:x));
 };

 const save=async()=>{
  setSaving(true);setError("");
  try{
   const cleanPrices=prices.filter(x=>x.bidder_name.trim()).map(x=>({
    bidder_name:x.bidder_name.trim(),rank:x.rank,bid_value:Number(x.bid_value||0),currency:(x.currency||"INR").toUpperCase(),
    is_ours:x.is_ours,source_reference:x.source_reference||null
   }));
   const payload={
    result_status:status,
    result_date:resultDate||null,
    our_rank:ourRank?Number(ourRank):null,
    our_bid_value:ourBidValue?Number(ourBidValue):null,
    our_margin_percent:margin?Number(margin):null,
    awarded_bidder:awardedBidder||null,
    win_reason:status==="Won"?(reason||null):null,
    loss_reason:status==="Lost"?(reason||null):null,
    source_reference:sourceReference||null,
    notes:notes||null,
    prices:cleanPrices
   };
   apply(await request<BidOutcomeResponse>("/bids/"+id+"/outcome",{method:"PUT",body:JSON.stringify(payload)}));
  }catch(e){setError(e instanceof Error?e.message:"Unable to save bid result.")}
  finally{setSaving(false)}
 };

 if(loading)return <LoadingState label="Loading bid result"/>;
 if(error&&!bid)return <ErrorState title="Bid result unavailable" message={error}/>;

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Bid Results"/>
  <PageHeader
   items={[{label:"Bid Workspace",href:"/bids"},{label:"Bid Results"}]}
   title="Bid Results"
   description="Capture the final tender outcome and ranked bidder prices for historical intelligence."
   action={<button onClick={save} disabled={saving} className="rounded bg-[#304354] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">{saving?"Saving...":"Save Result"}</button>}
  />
  {error&&<div className="mb-3"><ErrorState title="Unable to save" message={error}/></div>}
  {result?.warnings.length?<div className="mb-3 space-y-2">{result.warnings.map((x,i)=><div key={i} className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">{x}</div>)}</div>:null}

  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-5">
   <SummaryCard label="Result" value={status}/>
   <SummaryCard label="Our Rank" value={ourRank||"—"}/>
   <SummaryCard label="Our Bid Value" value={ourBidValue||"—"}/>
   <SummaryCard label="Gap to L1" value={result?.price_summary.our_gap_to_l1_percent!==null&&result?.price_summary.our_gap_to_l1_percent!==undefined?result.price_summary.our_gap_to_l1_percent+"%":"—"} tone={(result?.price_summary.our_gap_to_l1_percent||0)>0?"amber":undefined}/>
   <SummaryCard label="Recorded Margin" value={margin?margin+"%":"—"}/>
  </div>

  <section className="mb-3 rounded border border-slate-200 bg-white p-3">
   <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <Field label="Result Status"><select value={status} onChange={e=>setStatus(e.target.value)} className={inputClass}>{["Result Awaited","Won","Lost","No Bid","Cancelled","Pending"].map(x=><option key={x}>{x}</option>)}</select></Field>
    <Field label="Result Date"><input type="date" value={resultDate} onChange={e=>setResultDate(e.target.value)} className={inputClass}/></Field>
    <Field label="Our Rank"><input type="number" min="1" value={ourRank} onChange={e=>setOurRank(e.target.value)} className={inputClass} placeholder="e.g. 2"/></Field>
    <Field label="Our Bid Value"><input type="number" min="0" step="0.01" value={ourBidValue} onChange={e=>setOurBidValue(e.target.value)} className={inputClass}/></Field>
    <Field label="Our Margin %"><input type="number" step="0.01" value={margin} onChange={e=>setMargin(e.target.value)} className={inputClass}/></Field>
    <Field label="Awarded Bidder"><input value={awardedBidder} onChange={e=>setAwardedBidder(e.target.value)} className={inputClass}/></Field>
    <Field label="Source Reference"><input value={sourceReference} onChange={e=>setSourceReference(e.target.value)} className={inputClass} placeholder="Tender result / LOA reference"/></Field>
    <Field label={status==="Won"?"Win Reason":"Loss / Outcome Reason"}><input value={reason} onChange={e=>setReason(e.target.value)} className={inputClass}/></Field>
   </div>
   <div className="mt-3"><Field label="Notes"><textarea value={notes} onChange={e=>setNotes(e.target.value)} className={inputClass+" min-h-20"}/></Field></div>
  </section>

  <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white">
   <div className="border-b bg-slate-50 px-4 py-3"><h2 className="text-sm font-bold text-slate-900">L1 to L4 Bidder Prices</h2><p className="text-xs text-slate-500">Record only known result values. Mark exactly one row as ours where applicable.</p></div>
   <div className="space-y-2 p-3 md:hidden">{prices.map(row=><div key={row.rank} className="rounded border border-slate-200 p-3"><div className="mb-2 flex items-center justify-between"><div className="text-sm font-bold text-slate-900">L{row.rank}</div><label className="flex items-center gap-2 text-xs"><input type="radio" name="ours" checked={row.is_ours} onChange={()=>setPrices(rows=>rows.map(x=>({...x,is_ours:x.rank===row.rank})))} />Our Bid</label></div><div className="grid gap-2"><input value={row.bidder_name} onChange={e=>updatePrice(row.rank,{bidder_name:e.target.value})} className={inputClass} placeholder="Bidder name"/><input type="number" min="0" step="0.01" value={row.bid_value||""} onChange={e=>updatePrice(row.rank,{bid_value:Number(e.target.value)})} className={inputClass} placeholder="Bid value"/></div></div>)}</div>
   <div className="hidden overflow-x-auto md:block"><table className="w-full min-w-[900px] text-left text-xs"><thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr>{["Rank","Bidder","Bid Value","Currency","Our Bid","Source Reference"].map(h=><th key={h} className="px-3 py-2">{h}</th>)}</tr></thead><tbody>{prices.map(row=><tr key={row.rank} className="border-t"><td className="px-3 py-2 font-bold text-slate-800">L{row.rank}</td><td className="px-3 py-2"><input value={row.bidder_name} onChange={e=>updatePrice(row.rank,{bidder_name:e.target.value})} className={inputClass}/></td><td className="px-3 py-2"><input type="number" min="0" step="0.01" value={row.bid_value||""} onChange={e=>updatePrice(row.rank,{bid_value:Number(e.target.value)})} className={inputClass}/></td><td className="px-3 py-2"><input value={row.currency} onChange={e=>updatePrice(row.rank,{currency:e.target.value})} className={inputClass+" w-20"}/></td><td className="px-3 py-2 text-center"><input type="radio" name="ours-table" checked={row.is_ours} onChange={()=>setPrices(rows=>rows.map(x=>({...x,is_ours:x.rank===row.rank})))} /></td><td className="px-3 py-2"><input value={row.source_reference||""} onChange={e=>updatePrice(row.rank,{source_reference:e.target.value})} className={inputClass}/></td></tr>)}</tbody></table></div>
  </section>
 </div>;
}

function Field({label,children}:{label:string;children:ReactNode}){return <label className="block"><span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</span><div className="mt-1">{children}</div></label>}
