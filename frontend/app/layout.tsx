import "./globals.css";
import {Sidebar} from "@/components/Sidebar";
import {Header} from "@/components/Header";

export const metadata={title:"L&T Railway Bid Intelligence",description:"L&T Construction railway tender intelligence and bid readiness workspace"};

export default function Layout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><div className="min-h-screen bg-[#f3f5f7]"><Header/><Sidebar/><main className="pt-16 md:ml-[212px]"><div className="px-4 py-4 md:px-6 md:py-5">{children}</div></main></div></body></html>
}
