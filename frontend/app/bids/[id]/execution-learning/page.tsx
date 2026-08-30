"use client";

import {use,useEffect,useState,type ReactNode} from "react";
import {BidWorkspaceHeader} from "@/components/BidWorkspaceHeader";
import {ErrorState,LoadingState,PageHeader,SummaryCard} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid,ExecutionOutcomeResponse} from "@/types";

const inputClass="w-full rounded border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-800 outline-none focus:border-[#c69b2d] focus:ring-2 focus:ring-[#d5aa35]/20";

export default function ExecutionLearningPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [data,setData]=useState<ExecutionOutcomeResponse|null>(null);
 const [loading,setLoading]=useState(true);
 const [saving,setSaving]=useState(false);
 const [reviewing,setReviewing]=useState(false);
 const [error,setError]=useState("");
 const [form,setForm]=useState({
  execution_status:"Not Started",data_date:"",actual_start_date:"",actual_completion_date:"",
  final_contract_value:"",actual_cost:"",final_margin_percent:"",approved_variations:"",
  claims_recovered:"",eot_days:"",source_reference:"",notes:"",
 });

 const apply=(x:ExecutionOutcomeResponse)=>{
  setData(x);const e=x.execution;
  if(e)setForm({
   execution_status:e.execution_status,data_date:e.data_date||"",actual_start_date:e.actual_start_date||"",actual_completion_date:e.actual_completion_date||"",
   final_contract_value:e.final_contract_value===null?"":String(e.final_contract_value),actual_cost:e.actual_cost===null?"":String(e.actual_cost),
   final_margin_percent:e.final_margin_percent===null?"":String(e.final_margin_percent),approved_variations:e.approved_variations===null?"":String(e.approved_variations),
   claims_recovered:e.claims_recovered===null?"":String(e.claims_recovered),eot_days:e.eot_days===null?"":String(e.eot_days),
   source_reference:e.source_reference||"",notes:e.notes||"",
  });
 };

 useEffect(()=>{
  setLoading(true);setError("");
  request<Bid>("/bids/"+id).then(b=>{
   setBid(b);
   return request<ExecutionOutcomeResponse>("/bids/"+id+"/execution-outcome");
  }).then(apply).catch(e=>setError(e instanceof Error?e.message:"Unable to load execution learning.")).finally(()=>setLoading(false));
 },[id]);

 const set=(key:string,value:string)=>setForm(x=>({...x,[key]:value}));
 const num=(value:string)=>value===""?null:Number(value);
 const payload=()=>({
  execution_status:form.execution_status,data_date:form.data_date||null,actual_start_date:form.actual_start_date||null,actual_completion_date:form.actual_completion_date||null,
  final_contract_value:num(form.final_contract_value),actual_cost:num(form.actual_cost),final_margin_percent:num(form.final_margin_percent),
  approved_variations:num(form.approved_variations),claims_recovered:num(form.claims_recovered),eot_days:form.eot_days===""?null:Number(form.eot_days),
  source_reference:form.source_reference||null,notes:form.notes||null,
 });

 const save=async()=>{
  setSaving(true);setError("");
  try{apply(await request<ExecutionOutcomeResponse>("/bids/"+id+"/execution-outcome",{method:"PUT",body:JSON.stringify(payload())}))}
  catch(e){setError(e instanceof Error?e.message:"Unable to save execution actuals.")}
  finally{setSaving(false)}
 };
 const review=async()=>{
  setReviewing(true);setError("");
  try{apply(await request<ExecutionOutcomeResponse>("/bids/"+id+"/execution-outcome/review",{method:"POST"}))}
  catch(e){setError(e instanceof Error?e.message:"Unable to mark execution actuals reviewed.")}
  finally{setReviewing(false)}
 };

 if(loading)return <LoadingState label="Loading execution learning"/>;
 return <div className="mx-auto max-w-[1500px]">
  <BidWorkspaceHeader bid={bid} active="Execution Learning"/>
  <PageHeader items={[{label:"Bid Workspace",href:"/bids"},{label:"Execution Learning"}]} title="Bid vs Actual Execution Learning" description="Capture evidence-backed execution actuals and compare them with the recorded winning bid. Only reviewed actuals enter portfolio learning." action={<div className="flex gap-2"><button onClick={save} disabled={saving||!data} className="rounded bg-[#304354] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">{saving?"Saving...":"Save Actuals"}</button><button onClick={review} disabled={reviewing||!data?.execution||data.execution.review_status==="Reviewed"} className="rounded border border-[#c69b2d] bg-white px-4 py-2 text-xs font-semibold text-[#304354] disabled:opacity-50">{reviewing?"Reviewing...":"Mark Reviewed"}</button></div>}/>
  {error&&<div className="mb-3"><ErrorState message={error}/></div>}
  {!data?null:<>
   <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
    <SummaryCard label="Review Status" value={data.execution?.review_status||"Not Recorded"}/>
    <SummaryCard label="Bid Value" value={data.comparison.bid_value??"—"}/>
    <SummaryCard label="Final Contract Value" value={form.final_contract_value||"—"}/>
    <SummaryCard label="Revenue Change" value={data.comparison.revenue_change_vs_bid_percent!==null?data.comparison.revenue_change_vs_bid_percent+"%":"—"}/>
    <SummaryCard label="Bid Margin" value={data.comparison.bid_margin_percent!==null?data.comparison.bid_margin_percent+"%":"—"}/>
    <SummaryCard label="Final Margin" value={form.final_margin_percent?form.final_margin_percent+"%":"—"}/>
    <SummaryCard label="Margin Change" value={data.comparison.margin_change_percentage_points!==null?data.comparison.margin_change_percentage_points+" pp":"—"}/>
    <SummaryCard label="Actual Duration" value={data.comparison.actual_duration_days!==null?data.comparison.actual_duration_days+" days":"—"}/>
   </div>
   <section className="mb-3 rounded border border-slate-200 bg-white p-3">
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-sm font-bold text-slate-900">Reviewed Execution Actuals</h2><p className="text-xs text-slate-500">Editing any reviewed record returns it to Draft until it is reviewed again.</p></div><div className={data.learning_eligible?"text-xs font-semibold text-emerald-700":"text-xs font-semibold text-amber-700"}>{data.learning_eligible?"Included in portfolio learning":"Excluded from portfolio learning until reviewed"}</div></div>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
     <Field label="Execution Status"><select value={form.execution_status} onChange={e=>set("execution_status",e.target.value)} className={inputClass}>{["Not Started","In Progress","Completed","Closed"].map(x=><option key={x}>{x}</option>)}</select></Field>
     <Field label="Data Date"><input type="date" value={form.data_date} onChange={e=>set("data_date",e.target.value)} className={inputClass}/></Field>
     <Field label="Actual Start"><input type="date" value={form.actual_start_date} onChange={e=>set("actual_start_date",e.target.value)} className={inputClass}/></Field>
     <Field label="Actual Completion"><input type="date" value={form.actual_completion_date} onChange={e=>set("actual_completion_date",e.target.value)} className={inputClass}/></Field>
     <Field label="Final Contract Value"><input type="number" min="0" step="0.01" value={form.final_contract_value} onChange={e=>set("final_contract_value",e.target.value)} className={inputClass}/></Field>
     <Field label="Actual Cost"><input type="number" min="0" step="0.01" value={form.actual_cost} onChange={e=>set("actual_cost",e.target.value)} className={inputClass}/></Field>
     <Field label="Final Margin %"><input type="number" min="-100" max="100" step="0.01" value={form.final_margin_percent} onChange={e=>set("final_margin_percent",e.target.value)} className={inputClass}/></Field>
     <Field label="Approved Variations"><input type="number" min="0" step="0.01" value={form.approved_variations} onChange={e=>set("approved_variations",e.target.value)} className={inputClass}/></Field>
     <Field label="Claims Recovered"><input type="number" min="0" step="0.01" value={form.claims_recovered} onChange={e=>set("claims_recovered",e.target.value)} className={inputClass}/></Field>
     <Field label="EOT Days"><input type="number" min="0" step="1" value={form.eot_days} onChange={e=>set("eot_days",e.target.value)} className={inputClass}/></Field>
     <Field label="Source Reference"><input value={form.source_reference} onChange={e=>set("source_reference",e.target.value)} className={inputClass} placeholder="Certified final account / completion record"/></Field>
    </div>
    <div className="mt-3"><Field label="Notes"><textarea value={form.notes} onChange={e=>set("notes",e.target.value)} className={inputClass+" min-h-20"}/></Field></div>
   </section>
   <section className="rounded border border-slate-200 bg-white p-3">
    <h2 className="mb-3 text-sm font-bold text-slate-900">Deterministic Execution Ratios</h2>
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
     <SummaryCard label="Cost / Final Value" value={data.comparison.cost_to_final_value_percent!==null?data.comparison.cost_to_final_value_percent+"%":"—"}/>
     <SummaryCard label="Variation Share" value={data.comparison.variation_share_percent!==null?data.comparison.variation_share_percent+"%":"—"}/>
     <SummaryCard label="Claims Recovered Share" value={data.comparison.claims_recovered_share_percent!==null?data.comparison.claims_recovered_share_percent+"%":"—"}/>
     <SummaryCard label="EOT" value={form.eot_days?form.eot_days+" days":"—"}/>
    </div>
    <div className="mt-3 text-[10px] text-slate-500">{data.note}</div>
   </section>
  </>}
 </div>;
}

function Field({label,children}:{label:string;children:ReactNode}){return <label className="block"><span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</span><div className="mt-1">{children}</div></label>}
