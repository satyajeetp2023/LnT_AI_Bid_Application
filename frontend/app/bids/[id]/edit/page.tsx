"use client";

import {use,useEffect,useState} from "react";
import {Card} from "@/components/ui";
import {BidForm,BidFormData} from "@/features/bids/BidForm";
import {request} from "@/services/api";
import type {Bid} from "@/types";

export function bidToFormData(bid:Bid):Partial<BidFormData>{
 return {
  bid_id:bid.bid_id,
  tender_reference_no:bid.tender_reference_no,
  client:bid.client,
  tender_name:bid.tender_name,
  contract_type:bid.contract_type,
  project_type:bid.project_type,
  package_section:bid.package_section??"",
  location:bid.location??"",
  estimated_value:bid.estimated_value===null||bid.estimated_value===undefined?"":String(bid.estimated_value),
  currency:bid.currency,
  tender_due_date:bid.tender_due_date,
  pre_bid_meeting_date:bid.pre_bid_meeting_date??"",
  bid_manager:bid.bid_manager,
  co_bid_manager:bid.co_bid_manager??"",
  current_stage:bid.current_stage,
  bid_status:bid.bid_status,
  description:bid.description??"",
 };
}

export default function EditBid({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [bid,setBid]=useState<Bid|null>(null);
 const [error,setError]=useState("");

 useEffect(()=>{
  request<Bid>(`/bids/${id}`).then(setBid).catch(e=>setError(e instanceof Error?e.message:"Unable to load bid"));
 },[id]);

 if(error)return <Card className="p-6 text-red-700">{error}</Card>;
 if(!bid)return <Card className="p-10 text-center">Loading bid…</Card>;

 return <div className="mx-auto max-w-5xl">
  <h1 className="mb-5 text-2xl font-bold text-navy">Edit {bid.bid_id}</h1>
  <Card className="p-6">
   <BidForm initial={bidToFormData(bid)} bidDatabaseId={bid.id}/>
  </Card>
 </div>;
}
