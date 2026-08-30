"use client";

import {use,useEffect,useState,type ReactNode} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {ErrorState,LoadingState,PageHeader,StatusBadge,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,BidOutcomeResponse,HistoricalBidComparison,HistoricalBidImportPreview,HistoricalBidPrice} from "@/types";

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
 const [importing,setImporting]=useState(false);
 const [importPreview,setImportPreview]=useState<HistoricalBidImportPreview|null>(null);
 const [comparison,setComparison]=useState<HistoricalBidComparison|null>(null);

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
  Promise.all([request<Bid>("/bids/"+id),request<BidOutcomeResponse>("/bids/"+id+"/outcome"),request<HistoricalBidComparison>("/bids/"+id+"/historical-comparison")])
   .then(([b,o,h])=>{setBid(b);apply(o);setComparison(h)})
   .catch(()=>setError("Unable to load bid result information."))
   .finally(()=>setLoading(false));
 },[id]);

 const updatePrice=(rank:number,patch:Partial<HistoricalBidPrice>)=>{
  setPrices(rows=>rows.map(x=>x.rank===rank?{...x,...patch}:x));
 };
 const previewImport=async(file:File)=>{
  setImporting(true);setError("");
  try{
   const form=new FormData();form.append("file",file);
   const preview=await request<HistoricalBidImportPreview>("/bids/"+id+"/outcome/import-preview",{method:"POST",body:form});
   setImportPreview(preview);
   if(preview.detected){
    const candidate=preview.outcome_candidate;
    if(candidate){
     setStatus(candidate.result_status||"Result Awaited");
     setOurRank(candidate.our_rank?String(candidate.our_rank):"");
     setOurBidValue(candidate.our_bid_value!==null&&candidate.our_bid_value!==undefined?String(candidate.our_bid_value):"");
     setAwardedBidder(candidate.awarded_bidder||"");
     setSourceReference(candidate.source_reference||"");
    }
    const byRank=new Map(preview.prices.map(x=>[x.rank,x]));
    setPrices([1,2,3,4].map(rank=>byRank.get(rank)||emptyPrice(rank)));
   }
  }catch(e){setError(e instanceof Error?e.message:"Unable to preview historical result file.")}
  finally{setImporting(false)}
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
 if(error&&!bid)return <ErrorState message={error}/>;

 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Bid Results"/>
  <PageHeader
   items={[{label:"Bid Workspace",href:"/bids"},{label:"Bid Results"}]}
   title="Bid Results"
   description="Capture the final tender outcome and ranked bidder prices for historical intelligence."
   action={<button onClick={save} disabled={saving} className="rounded bg-[#304354] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">{saving?"Saving...":"Save Result"}</button>}
  />
  {error&&<div className="mb-3"><ErrorState message={error}/></div>}
  {result?.warnings.length?<div className="mb-3 space-y-2">{result.warnings.map((x,i)=><div key={i} className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">{x}</div>)}</div>:null}

  <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-5">
   <SummaryCard label="Result" value={status}/>
   <SummaryCard label="Our Rank" value={ourRank||"—"}/>
   <SummaryCard label="Our Bid Value" value={ourBidValue||"—"}/>
   <SummaryCard label="Gap to L1" value={result?.price_summary.our_gap_to_l1_percent!==null&&result?.price_summary.our_gap_to_l1_percent!==undefined?result.price_summary.our_gap_to_l1_percent+"%":"—"} tone={(result?.price_summary.our_gap_to_l1_percent||0)>0?"amber":undefined}/>
   <SummaryCard label="Recorded Margin" value={margin?margin+"%":"—"}/>
  </div>

  <section className="mb-3 overflow-hidden rounded border border-slate-200 bg-white">
   <div className="border-b bg-slate-50 px-4 py-3">
    <h2 className="text-sm font-bold text-slate-900">Comparable Historical Bids</h2>
    <p className="text-xs text-slate-500">Deterministic comparison against completed bids you are authorized to see. This is descriptive only, not a win prediction.</p>
   </div>
   {comparison&&comparison.matches.length>0?<>
    <div className="grid grid-cols-2 gap-3 border-b p-3 md:grid-cols-5">
     <SummaryCard label="Comparable" value={comparison.summary.comparable_bids}/>
     <SummaryCard label="Won" value={comparison.summary.won??0} tone="green"/>
     <SummaryCard label="Lost" value={comparison.summary.lost??0} tone="red"/>
     <SummaryCard label="Historical Win Rate" value={comparison.summary.win_rate_percent!==null&&comparison.summary.win_rate_percent!==undefined?comparison.summary.win_rate_percent+"%":"—"}/>
     <SummaryCard label="Avg Gap to L1" value={comparison.summary.average_gap_to_l1_percent!==null&&comparison.summary.average_gap_to_l1_percent!==undefined?comparison.summary.average_gap_to_l1_percent+"%":"—"}/>
    </div>
    <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-xs">
     <thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">Bid</th><th className="px-3 py-2">Client</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Result</th><th className="px-3 py-2">Our Rank</th><th className="px-3 py-2">Gap to L1</th><th className="px-3 py-2">Similarity</th><th className="px-3 py-2">Matched On</th></tr></thead>
     <tbody>{comparison.matches.map(x=><tr key={x.bid_project_id} className="border-t"><td className="px-3 py-3"><div className="font-semibold text-slate-900">{x.bid_id}</div><div className="text-[10px] text-slate-500">{x.tender_name}</div></td><td className="px-3 py-3">{x.client}</td><td className="px-3 py-3">{x.project_type}</td><td className="px-3 py-3"><StatusBadge value={x.result_status}/></td><td className="px-3 py-3">{x.our_rank??"—"}</td><td className="px-3 py-3">{x.our_gap_to_l1_percent!==null?x.our_gap_to_l1_percent+"%":"—"}</td><td className="px-3 py-3 font-semibold">{x.similarity_score}%</td><td className="px-3 py-3">{x.matched_fields.map(v=>v.replaceAll("_"," ")).join(", ")}</td></tr>)}</tbody>
    </table></div>
    <div className="border-t bg-slate-50 px-4 py-2 text-[10px] text-slate-500">{comparison.methodology}</div>
   </>:<div className="p-4 text-xs text-slate-500">No completed comparable historical bids are available yet.</div>}
  </section>

  <section className="mb-3 rounded border border-slate-200 bg-white p-3">
   <div className="flex flex-wrap items-center justify-between gap-3">
    <div><div className="text-sm font-bold text-slate-900">Import Tender Result</div><div className="text-xs text-slate-500">Upload CSV/XLSX result tabulation. The system prepares a preview only. Nothing is saved until you review and click Save Result.</div></div>
    <label className="cursor-pointer rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-[#d5aa35]">
     {importing?"Reading...":"Choose Result File"}
     <input type="file" accept=".csv,.xlsx" className="hidden" disabled={importing} onChange={e=>{const file=e.target.files?.[0];if(file)previewImport(file);e.currentTarget.value=""}}/>
    </label>
   </div>
   {importPreview&&<div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
    <div className="font-semibold">{importPreview.detected?"Preview loaded from "+importPreview.source_filename:"Result structure not detected"}</div>
    <div className="mt-1">{importPreview.note||"Review the extracted values before saving."}</div>
    {importPreview.warnings.length>0&&<ul className="mt-2 list-disc space-y-1 pl-5">{importPreview.warnings.map((x,i)=><li key={i}>{x}</li>)}</ul>}
   </div>}
  </section>

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
