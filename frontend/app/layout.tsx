import "./globals.css";
import {AppShell} from "@/components/AppShell";

export const metadata={title:"L&T Railway Bid Intelligence",description:"L&T Construction railway tender intelligence and bid readiness workspace"};

export default function Layout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><AppShell>{children}</AppShell></body></html>
}
