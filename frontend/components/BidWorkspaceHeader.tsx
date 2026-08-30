"use client";
import Link from "next/link";
import {CalendarDays,MapPin} from "lucide-react";
import type {Bid} from "@/types";
import {StatusBadge} from "@/components/design-system";

const steps=["Documents","Requirement Register","Missing Inputs","Pre-Bid Queries","Work Queue","Bid Preparation","Schedules","Copilot","Review","Submission","Bid Results"];

export function BidWorkspaceHeader({bid,active}:{bid:Bid|null;active:"Documents"|"Requirement Register"|"Missing Inputs"|"Pre-Bid Queries"|"Work Queue"|"Bid Preparation"|"Schedules"|"Copilot"|"Review"|"Submission"|"Bid Results"}){
 if(!bid)return null;
 return <section className="mb-3 overflow-hidden border border-slate-200 bg-white">
  <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2">
   <div className="min-w-0">
    <div className="flex flex-wrap items-center gap-2">
     <h2 className="truncate text-[14px] font-semibold text-[#243241]">{bid.tender_name}</h2>
     <StatusBadge tone={bid.bid_status==="Draft"?"grey":"green"}>{bid.bid_status}</StatusBadge>
    </div>
    <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[9.5px] text-slate-500">
     <span className="font-semibold text-slate-700">Bid ID: {bid.bid_id}</span><span>{bid.client}</span>{bid.location&&<span className="flex items-center gap-1"><MapPin size={10}/>{bid.location}</span>}<span className="flex items-center gap-1"><CalendarDays size={10}/>Submission: {new Date(bid.tender_due_date+"T00:00:00").toLocaleDateString()}</span>
    </div>
   </div>
   <div className="text-[9px] font-semibold uppercase tracking-[.16em] text-[#8a6a16]">Bid Workspace</div>
  </div>
  <nav aria-label="Bid workflow" className="flex overflow-x-auto border-t border-slate-200 bg-[#f7f8f9] md:grid md:grid-cols-11">
   {steps.map((step,index)=>{const available=index<11,selected=step===active;const route=index===0?"documents":index===1?"requirements":index===2?"missing-inputs":index===3?"pre-bid-queries":index===4?"work-queue":index===5?"bid-preparation":index===6?"schedules":index===7?"copilot":index===8?"review-approval":index===9?"submission":"bid-results";return available?<Link key={step} href={`/bids/${bid.id}/${route}`} className={`min-w-[145px] shrink-0 border-r border-slate-200 px-3 py-2 text-center text-[9.5px] md:min-w-0 md:py-1.5 font-semibold ${selected?"border-b-2 border-b-[#e2b635] bg-white text-[#243241]":"text-slate-500 hover:bg-white hover:text-[#243241]"}`}>{index+1}. {step}</Link>:<div key={step} aria-disabled="true" className="min-w-[145px] shrink-0 border-r border-slate-200 px-3 py-2 text-center text-[9.5px] text-slate-400 md:min-w-0 md:py-1.5">{index+1}. {step}</div>})}
  </nav>
 </section>
}
