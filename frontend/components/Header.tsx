import {Bell,HelpCircle,Search} from "lucide-react";
import {LTConstructionLogo} from "@/components/LTConstructionLogo";

export function Header(){
 return <header className="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between border-b border-[#44505a] bg-[#354654] px-4 text-white shadow-sm">
  <div className="flex min-w-0 items-center gap-3">
   <div className="flex h-9 items-center bg-white px-2.5">
    <LTConstructionLogo className="h-[22px] w-auto object-contain"/>
   </div>
   <div className="hidden h-7 w-px bg-white/20 sm:block"/>
   <div className="min-w-0">
    <div className="truncate text-[14px] font-semibold text-[#e2b635]">L&amp;T Bid Intelligence</div>
    <div className="truncate text-[10px] text-slate-300">Prepare. Compete. Win.</div>
   </div>
  </div>
  <div className="flex items-center gap-1.5">
   <button aria-label="Search" className="rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><Search size={17}/></button>
   <button aria-label="Notifications" className="relative rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><Bell size={17}/><span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-[#e2b635]"/></button>
   <button aria-label="Help" className="rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><HelpCircle size={17}/></button>
   <div className="mx-1 hidden h-7 w-px bg-white/15 sm:block"/>
   <div className="hidden text-right md:block"><div className="text-[11px] font-semibold">Arun Kumar</div><div className="text-[9px] text-slate-300">Bid Manager</div></div>
   <div className="grid h-8 w-8 place-items-center rounded-full bg-[#e2b635] text-[10px] font-bold text-[#24313d]">AK</div>
  </div>
 </header>
}
