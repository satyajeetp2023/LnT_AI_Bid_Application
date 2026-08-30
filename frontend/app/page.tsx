"use client";

import Link from "next/link";
import {useCallback,useEffect,useState} from "react";
import {ArrowRight,Clock3,FileText,FolderKanban,TriangleAlert} from "lucide-react";
import {Badge,Card} from "@/components/ui";
import {PrimaryButton,PrimaryLink} from "@/components/design-system";
import {request} from "@/services/api";
import type {Bid} from "@/types";

type Summary={
 active_bids:number;
 bids_due_soon:number;
 documents_uploaded:number;
 documents_requiring_review:number;
 recent_bids:Bid[];
};

export default function Dashboard(){
 const [data,setData]=useState<Summary|null>(null);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);

 const load=useCallback(async()=>{
  setLoading(true);
  setError("");
  const controller=new AbortController();
  const timer=window.setTimeout(()=>controller.abort(),15000);
  try{
   const summary=await request<Summary>("/dashboard/summary",{signal:controller.signal});
   setData(summary);
  }catch(e){
   if(e instanceof DOMException&&e.name==="AbortError"){
    setError("Dashboard service did not respond within 15 seconds. Check that the backend is running, then retry.");
   }else{
    setError(e instanceof Error?e.message:"Unable to load dashboard.");
   }
  }finally{
   window.clearTimeout(timer);
   setLoading(false);
  }
 },[]);

 useEffect(()=>{void load()},[load]);

 if(loading&&!data)return <Card className="p-10 text-center">Loading dashboard…</Card>;
 if(error&&!data)return <Card className="border-red-200 p-6 text-red-700"><div>Unable to load dashboard: {error}</div><PrimaryButton className="mt-4" onClick={()=>void load()}>Retry Dashboard</PrimaryButton></Card>;
 if(!data)return null;

 const cards=[
  ["Active Bids",data.active_bids,"Authorized active projects",FolderKanban],
  ["Bids Due Soon",data.bids_due_soon,"Next 30 days",Clock3],
  ["Documents Uploaded",data.documents_uploaded,"Non-archived documents",FileText],
  ["Requiring Review",data.documents_requiring_review,"Classification pending",TriangleAlert],
 ] as const;

 return <div className="mx-auto max-w-7xl">
  <div className="mb-6 flex items-end justify-between gap-3">
   <div><h1 className="text-2xl font-bold text-navy">Bid Portfolio Dashboard</h1><p className="mt-1 text-sm text-slate-500">Live document readiness overview</p></div>
   <PrimaryLink href="/bids/new">+ Create New Bid</PrimaryLink>
  </div>
  <div className="grid gap-4 md:grid-cols-4">
   {cards.map(([a,b,c,I])=><Card key={a} className="p-5"><div className="flex justify-between"><div className="text-xs font-bold uppercase text-slate-500">{a}</div><I size={20}/></div><div className="mt-3 text-3xl font-bold text-navy">{b}</div><div className="text-xs text-slate-500">{c}</div></Card>)}
  </div>
  <Card className="mt-6 overflow-x-auto">
   <div className="flex justify-between border-b p-5"><h2 className="font-bold text-navy">Recently Updated Bids</h2><Link href="/bids" className="flex gap-1 text-sm font-semibold text-blue-700">View all <ArrowRight size={14}/></Link></div>
   {data.recent_bids.length===0?<div className="p-10 text-center text-slate-500">No authorized bids yet.</div>:<table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{["Bid ID","Tender Name","Client","Contract Type","Due Date","Stage","Status","Bid Manager"].map(x=><th className="px-5 py-3" key={x}>{x}</th>)}</tr></thead><tbody>{data.recent_bids.map(b=><tr key={b.id} className="border-t"><td className="px-5 py-4"><Link className="font-bold text-blue-700" href={`/bids/${b.id}/documents`}>{b.bid_id}</Link></td><td className="px-5 font-semibold">{b.tender_name}</td><td className="px-5">{b.client}</td><td className="px-5">{b.contract_type}</td><td className="px-5">{b.tender_due_date}</td><td className="px-5"><Badge>{b.current_stage}</Badge></td><td className="px-5"><Badge tone={b.bid_status==="Draft"?"grey":"green"}>{b.bid_status}</Badge></td><td className="px-5">{b.bid_manager}</td></tr>)}</tbody></table>}
  </Card>
 </div>;
}
