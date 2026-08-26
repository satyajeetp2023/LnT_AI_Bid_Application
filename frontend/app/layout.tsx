import "./globals.css";
import {Sidebar} from "@/components/Sidebar";
import {Header} from "@/components/Header";

export const metadata={title:"L&T Railway Bid Intelligence",description:"L&T Construction railway tender intelligence and bid readiness workspace"};

export default function Layout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><div className="flex min-h-screen"><Sidebar/><div className="min-w-0 flex-1 md:ml-64"><Header/><main className="p-4 md:p-6 lg:p-7">{children}</main></div></div></body></html>
}
