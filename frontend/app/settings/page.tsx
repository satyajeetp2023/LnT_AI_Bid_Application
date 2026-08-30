"use client";

import {useEffect,useState} from "react";
import {PageHeader,LoadingState,ErrorState} from "@/components/design-system";
import {request} from "@/services/api";

type Me={id:number;name:string;roles:string[];permissions:string[]};

export default function SettingsPage(){
 const [me,setMe]=useState<Me|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{request<Me>("/auth/me").then(setMe).catch(e=>setError(e instanceof Error?e.message:"Unable to load profile"))},[]);
 return <div className="mx-auto max-w-[1100px]">
  <PageHeader items={[{label:"Settings"}]} title="Settings & Help" description="Your profile, access context and application guidance."/>
  {error?<ErrorState message={error}/>:!me?<LoadingState label="Loading settings…"/>:<div className="grid gap-3 lg:grid-cols-2">
   <section className="rounded border border-slate-200 bg-white p-4">
    <h2 className="text-sm font-bold text-slate-900">Profile</h2>
    <div className="mt-3 space-y-2 text-xs text-slate-700">
     <div><span className="text-slate-500">Name</span><div className="font-semibold">{me.name}</div></div>
     <div><span className="text-slate-500">Roles</span><div className="font-semibold">{me.roles.join(", ")||"No role assigned"}</div></div>
     <div><span className="text-slate-500">Access</span><div>{me.permissions.length} effective permission{me.permissions.length===1?"":"s"}</div></div>
    </div>
   </section>
   <section id="help" className="rounded border border-slate-200 bg-white p-4">
    <h2 className="text-sm font-bold text-slate-900">Help</h2>
    <p className="mt-2 text-xs leading-5 text-slate-600">Use the left navigation to move through a bid. Open a bid first for bid-specific modules. If access is restricted, the application will show an intentional access-denied page instead of a generic failure.</p>
    <p className="mt-2 text-xs leading-5 text-slate-600">A visual downloadable user manual will be provided as the final navigation option in the completed application.</p>
   </section>
   <section className="rounded border border-slate-200 bg-white p-4">
    <h2 className="text-sm font-bold text-slate-900">AI & Intelligence Status</h2>
    <p className="mt-2 text-xs leading-5 text-slate-600">Bid-scoped AI/provider status is shown inside Bid Intelligence Copilot so users can see whether semantic AI, lexical retrieval or another approved provider mode is active for that tender.</p>
   </section>
   <section className="rounded border border-slate-200 bg-white p-4">
    <h2 className="text-sm font-bold text-slate-900">Security & Access</h2>
    <p className="mt-2 text-xs leading-5 text-slate-600">Access is controlled by authenticated identity, role permissions and bid membership. Administration controls are shown only when an authorized management module is available.</p>
   </section>
  </div>}
 </div>;
}
