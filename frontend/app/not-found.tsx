import Link from "next/link";
import {FileQuestion} from "lucide-react";

export default function NotFound(){
 return <div className="mx-auto max-w-2xl py-12">
  <div className="rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
   <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-slate-600"><FileQuestion size={24}/></div>
   <h1 className="mt-4 text-xl font-bold text-slate-900">Page Not Found</h1>
   <p className="mt-2 text-sm leading-6 text-slate-600">The page may have moved, the link may be outdated, or the module may not be available in this release.</p>
   <div className="mt-6 flex flex-wrap justify-center gap-2">
    <Link href="/" className="rounded bg-[#304354] px-4 py-2 text-sm font-semibold text-white">Dashboard</Link>
    <Link href="/bids" className="rounded border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">My Bids</Link>
   </div>
  </div>
 </div>;
}
