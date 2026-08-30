import type {NextConfig} from "next";

const isProd=process.env.NODE_ENV==="production";
const scriptSrc=isProd?"'self' 'unsafe-inline'":"'self' 'unsafe-inline' 'unsafe-eval'";
const csp=[
 "default-src 'self'",
 "base-uri 'self'",
 "object-src 'none'",
 "frame-ancestors 'none'",
 "form-action 'self'",
 "img-src 'self' data: blob:",
 "font-src 'self' data:",
 "style-src 'self' 'unsafe-inline'",
 `script-src ${scriptSrc}`,
 "connect-src 'self' https: http:",
 "worker-src 'self' blob:",
].join("; ");

const nextConfig:NextConfig={
 async headers(){
  return [{
   source:"/:path*",
   headers:[
    {key:"Content-Security-Policy",value:csp},
    {key:"X-Frame-Options",value:"DENY"},
    {key:"X-Content-Type-Options",value:"nosniff"},
    {key:"Referrer-Policy",value:"no-referrer"},
    {key:"Permissions-Policy",value:"camera=(), microphone=(), geolocation=()"},
    {key:"Cache-Control",value:"no-store"},
   ],
  }];
 },
};

export default nextConfig;
