import {Bell,HelpCircle} from "lucide-react";
import {LTConstructionLogo} from "@/components/LTConstructionLogo";

export function Header(){
 return <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-[0_1px_2px_rgba(15,23,42,.03)] md:px-6">
  <div className="flex min-w-0 items-center gap-3">
   <LTConstructionLogo className="h-8 w-auto object-contain md:hidden"/>
   <div className="min-w-0">
    <div className="truncate text-[11px] font-bold uppercase tracking-[.16em] text-[#005596]">Railway SBG</div>
    <div className="truncate text-sm font-semibold text-slate-700">Bid Intelligence &amp; Readiness Workspace</div>
   </div>
  </div>
  <div className="flex items-center gap-2 sm:gap-3">
   <button aria-label="Help" className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-[#005596]"><HelpCircle size={17}/></button>
   <button aria-label="Notifications" className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-[#005596]"><Bell size={17}/></button>
   <div className="hidden h-7 w-px bg-slate-200 sm:block"/>
   <div className="hidden text-right md:block"><div className="text-xs font-semibold text-slate-800">Bid Workspace User</div><div className="text-[10px] text-slate-500">Development Access</div></div>
   <div className="grid h-9 w-9 place-items-center rounded-full bg-[#005596] text-[10px] font-bold text-white shadow-sm">BW</div>
  </div>
 </header>
}
