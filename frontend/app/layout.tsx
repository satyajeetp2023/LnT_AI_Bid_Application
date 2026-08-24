import "./globals.css";import {Sidebar} from "@/components/Sidebar";import {Header} from "@/components/Header";
export const metadata={title:"Railway Bid Intelligence",description:"Enterprise bid readiness workspace"};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body><div className="flex min-h-screen"><Sidebar/><div className="min-w-0 flex-1 md:ml-64"><Header/><main className="p-4 md:p-7">{children}</main></div></div></body></html>}
