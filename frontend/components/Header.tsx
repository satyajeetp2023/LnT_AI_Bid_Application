"use client";

import {useEffect,useMemo,useState} from "react";
import {Bell,HelpCircle,Menu,Search} from "lucide-react";
import {LTConstructionLogo} from "@/components/LTConstructionLogo";
import {request} from "@/services/api";

type Me={id:number;name:string;roles:string[]};

function initials(name:string){
 const parts=name.trim().split(/\s+/).filter(Boolean);
 if(parts.length===0)return "?";
 return (parts[0][0]+(parts.length>1?parts[parts.length-1][0]:"")).toUpperCase();
}

export function Header({onMenu}:{onMenu?:()=>void}){
 const [me,setMe]=useState<Me|null>(null);
 useEffect(()=>{let active=true;request<Me>("/auth/me").then(x=>{if(active)setMe(x)}).catch(()=>{});return()=>{active=false}},[]);
 const displayName=me?.name||"Signed-in User";
 const role=me?.roles?.[0]||"Authorized User";
 const avatar=useMemo(()=>initials(displayName),[displayName]);

 return <header className="fixed inset-x-0 top-0 z-50 flex h-[58px] items-center justify-between border-b border-[#44505a] bg-[#354654] px-4 text-white shadow-sm">
  <div className="flex min-w-0 items-center gap-2 sm:gap-3"><button onClick={onMenu} aria-label="Open navigation" className="rounded p-2 text-slate-200 hover:bg-white/10 md:hidden"><Menu size={20}/></button>
   <div className="flex h-10 w-[170px] shrink-0 sm:h-11 sm:w-[220px] items-center justify-center overflow-hidden bg-white">
    <LTConstructionLogo className="w-[162px] max-w-none sm:w-[210px] shrink-0 object-contain"/>
   </div>
   <div className="hidden h-7 w-px bg-white/20 sm:block"/>
   <div className="min-w-0">
    <div className="truncate text-[14px] font-semibold text-[#e2b635]">L&amp;T Bid Intelligence</div>
    <div className="truncate text-[9.5px] leading-3 text-slate-300">Prepare. Compete. Win.</div>
   </div>
  </div>
  <div className="flex items-center gap-1.5">
   <button aria-label="Search" className="hidden rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white sm:block"><Search size={17}/></button>
   <button aria-label="Notifications" className="relative rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><Bell size={17}/></button>
   <button aria-label="Help" className="rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><HelpCircle size={17}/></button>
   <div className="mx-1 hidden h-7 w-px bg-white/15 sm:block"/>
   <div className="hidden text-right md:block"><div className="max-w-[170px] truncate text-[11px] font-semibold">{displayName}</div><div className="max-w-[170px] truncate text-[9px] text-slate-300">{role}</div></div>
   <div className="grid h-8 w-8 place-items-center rounded-full bg-[#e2b635] text-[10px] font-bold text-[#24313d]" aria-label={displayName}>{avatar}</div>
  </div>
 </header>;
}
