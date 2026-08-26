import {Bell,HelpCircle,Search} from "lucide-react";

export function Header(){
 return <header className="flex h-16 items-center justify-between border-b border-[#435363] bg-[#394957] px-5 text-white md:px-6">
  <div className="min-w-0">
   <div className="flex items-center gap-3">
    <span className="text-[14px] font-semibold text-[#d5aa35]">L&amp;T Bid Intelligence</span>
    <span className="hidden h-5 w-px bg-white/20 sm:block"/>
    <span className="hidden text-[11px] text-slate-300 sm:inline">Prepare. Compete. Win.</span>
   </div>
  </div>
  <div className="flex items-center gap-1.5 sm:gap-2">
   <button aria-label="Search" className="rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><Search size={17}/></button>
   <button aria-label="Notifications" className="relative rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><Bell size={17}/><span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[#d5aa35]"/></button>
   <button aria-label="Help" className="rounded p-2 text-slate-300 hover:bg-white/10 hover:text-white"><HelpCircle size={17}/></button>
   <div className="mx-1 hidden h-7 w-px bg-white/15 sm:block"/>
   <div className="hidden text-right md:block"><div className="text-[11px] font-semibold text-white">Arun Kumar</div><div className="text-[9px] text-slate-300">Bid Manager</div></div>
   <div className="grid h-8 w-8 place-items-center rounded-full bg-[#d5aa35] text-[10px] font-bold text-[#283746]">AK</div>
  </div>
 </header>
}
