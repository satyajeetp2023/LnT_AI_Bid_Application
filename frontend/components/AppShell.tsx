"use client";

import {useState} from "react";
import {Header} from "@/components/Header";
import {Sidebar} from "@/components/Sidebar";

export function AppShell({children}:{children:React.ReactNode}){
 const [mobileNavOpen,setMobileNavOpen]=useState(false);
 return <div className="min-h-screen bg-[#f3f5f7]">
  <Header onMenu={()=>setMobileNavOpen(true)}/>
  <Sidebar mobileOpen={mobileNavOpen} onClose={()=>setMobileNavOpen(false)}/>
  <main className="pt-[58px] md:ml-[204px]">
   <div className="px-3 py-3 sm:px-4 md:px-5 md:py-4">{children}</div>
  </main>
 </div>;
}
