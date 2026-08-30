const MODE=process.env.NEXT_PUBLIC_AUTH_MODE||"development_header";
const AUTHORITY=process.env.NEXT_PUBLIC_OIDC_AUTHORITY||"";
const CLIENT_ID=process.env.NEXT_PUBLIC_OIDC_CLIENT_ID||"";
const REDIRECT_URI=process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI||"";
const SCOPE=process.env.NEXT_PUBLIC_OIDC_SCOPE||"openid profile email";

const TOKEN_KEY="railway_bid_access_token";
const EXPIRY_KEY="railway_bid_access_token_expiry";
const STATE_KEY="railway_bid_oidc_state";
const VERIFIER_KEY="railway_bid_pkce_verifier";
const RETURN_KEY="railway_bid_auth_return";

type Discovery={authorization_endpoint:string;token_endpoint:string};

function base64url(bytes:Uint8Array){
 let binary="";
 bytes.forEach(b=>binary+=String.fromCharCode(b));
 return btoa(binary).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
}
function randomValue(length=32){const bytes=new Uint8Array(length);crypto.getRandomValues(bytes);return base64url(bytes)}
async function challenge(verifier:string){
 const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(verifier));
 return base64url(new Uint8Array(digest));
}
async function discovery():Promise<Discovery>{
 if(!AUTHORITY)throw new Error("OIDC authority is not configured");
 const url=AUTHORITY.replace(/\/$/,"")+"/.well-known/openid-configuration";
 const response=await fetch(url,{cache:"no-store"});
 if(!response.ok)throw new Error("Unable to load enterprise identity configuration");
 const data=await response.json();
 if(!data.authorization_endpoint||!data.token_endpoint)throw new Error("Enterprise identity configuration is incomplete");
 return data;
}
export function authMode(){return MODE}
export function clearAccessToken(){
 if(typeof window==="undefined")return;
 sessionStorage.removeItem(TOKEN_KEY);sessionStorage.removeItem(EXPIRY_KEY);
}
export function getAccessToken(){
 if(typeof window==="undefined"||MODE!=="oidc")return null;
 const token=sessionStorage.getItem(TOKEN_KEY);
 const expiry=Number(sessionStorage.getItem(EXPIRY_KEY)||0);
 if(!token||!expiry||Date.now()>=expiry-30000){clearAccessToken();return null}
 return token;
}
export async function beginLogin(returnTo?:string){
 if(typeof window==="undefined"||MODE!=="oidc")return;
 if(!CLIENT_ID||!REDIRECT_URI)throw new Error("Enterprise OIDC client configuration is incomplete");
 const config=await discovery();
 const verifier=randomValue(48);const state=randomValue(24);
 sessionStorage.setItem(VERIFIER_KEY,verifier);sessionStorage.setItem(STATE_KEY,state);
 sessionStorage.setItem(RETURN_KEY,returnTo||window.location.pathname+window.location.search);
 const params=new URLSearchParams({
  response_type:"code",client_id:CLIENT_ID,redirect_uri:REDIRECT_URI,scope:SCOPE,
  state,code_challenge:await challenge(verifier),code_challenge_method:"S256",
 });
 window.location.assign(config.authorization_endpoint+"?"+params.toString());
}
export async function handleCallback(search:string){
 if(typeof window==="undefined")throw new Error("OIDC callback requires a browser");
 const params=new URLSearchParams(search);
 const error=params.get("error");
 if(error)throw new Error(params.get("error_description")||error);
 const code=params.get("code");const state=params.get("state");
 const expected=sessionStorage.getItem(STATE_KEY);const verifier=sessionStorage.getItem(VERIFIER_KEY);
 if(!code||!state||!expected||state!==expected||!verifier)throw new Error("OIDC callback state validation failed");
 const config=await discovery();
 const body=new URLSearchParams({
  grant_type:"authorization_code",code,client_id:CLIENT_ID,redirect_uri:REDIRECT_URI,code_verifier:verifier,
 });
 const response=await fetch(config.token_endpoint,{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});
 if(!response.ok)throw new Error("Enterprise identity token exchange failed");
 const data=await response.json();
 if(!data.access_token)throw new Error("Enterprise identity provider returned no access token");
 const expires=Math.max(60,Number(data.expires_in||3600));
 sessionStorage.setItem(TOKEN_KEY,data.access_token);
 sessionStorage.setItem(EXPIRY_KEY,String(Date.now()+expires*1000));
 sessionStorage.removeItem(STATE_KEY);sessionStorage.removeItem(VERIFIER_KEY);
 const returnTo=sessionStorage.getItem(RETURN_KEY)||"/";
 sessionStorage.removeItem(RETURN_KEY);
 return returnTo.startsWith("/")&&!returnTo.startsWith("//")?returnTo:"/";
}
