import {afterEach,beforeEach,describe,expect,test,vi} from "vitest";

const beginLogin=vi.fn();
let mode="development_header";
let token:string|null=null;
vi.mock("@/services/auth",()=>({
 authMode:()=>mode,
 beginLogin:(...args:unknown[])=>beginLogin(...args),
 getAccessToken:()=>token,
}));

describe("GAP-002 API request timeout and cancellation",()=>{
 beforeEach(()=>{vi.useFakeTimers();mode="development_header";token=null;beginLogin.mockReset()});
 afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();vi.unstubAllGlobals()});

 test("aborts an unresponsive request with a clear timeout error",async()=>{
  vi.stubGlobal("fetch",vi.fn((_url:RequestInfo|URL,init?:RequestInit)=>new Promise((_resolve,reject)=>{
   if(init?.signal?.aborted){reject(new DOMException("Aborted","AbortError"));return}
   init?.signal?.addEventListener("abort",()=>reject(new DOMException("Aborted","AbortError")),{once:true});
  })));
  const {request}=await import("./api");
  const pending=request("/slow",{timeoutMs:25,retries:0});
  const rejection=expect(pending).rejects.toThrow("did not respond within 1 seconds");
  await vi.advanceTimersByTimeAsync(25);
  await rejection;
 });

 test("honours caller cancellation without reporting a timeout",async()=>{
  vi.stubGlobal("fetch",vi.fn((_url:RequestInfo|URL,init?:RequestInit)=>new Promise((_resolve,reject)=>{
   if(init?.signal?.aborted){reject(new DOMException("Aborted","AbortError"));return}
   init?.signal?.addEventListener("abort",()=>reject(new DOMException("Aborted","AbortError")),{once:true});
  })));
  const {request}=await import("./api");
  const controller=new AbortController();
  const pending=request("/cancel",{signal:controller.signal,timeoutMs:5000,retries:0});
  const rejection=expect(pending).rejects.toMatchObject({name:"AbortError"});
  controller.abort();
  await rejection;
 });

 test("keeps timeout active while consuming the response body",async()=>{
  vi.stubGlobal("fetch",vi.fn((_url:RequestInfo|URL,init?:RequestInit)=>Promise.resolve(new Response(new ReadableStream({
   start(controller){
    init?.signal?.addEventListener("abort",()=>controller.error(new DOMException("Aborted","AbortError")),{once:true});
   },
  }),{status:200,headers:{"Content-Type":"application/json"}}))));
  const {request}=await import("./api");
  const pending=request("/slow-body",{timeoutMs:25,retries:0});
  const rejection=expect(pending).rejects.toThrow("did not respond within 1 seconds");
  await vi.advanceTimersByTimeAsync(25);
  await rejection;
 });

 test("clears the timeout after a successful response body is consumed",async()=>{
  const clearSpy=vi.spyOn(globalThis,"clearTimeout");
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify({ok:true}),{status:200,headers:{"Content-Type":"application/json"}})));
  const {request}=await import("./api");
  await expect(request<{ok:boolean}>("/ok",{timeoutMs:1000,retries:0})).resolves.toEqual({ok:true});
  expect(clearSpy).toHaveBeenCalled();
 });

 test("does not retry after starting an OIDC login transition",async()=>{
  mode="oidc";
  token=null;
  beginLogin.mockResolvedValue(undefined);
  const fetchMock=vi.fn();
  vi.stubGlobal("fetch",fetchMock);
  const {request}=await import("./api");
  await expect(request("/secure",{retries:1})).rejects.toMatchObject({name:"AuthTransitionError"});
  expect(beginLogin).toHaveBeenCalledOnce();
  expect(fetchMock).not.toHaveBeenCalled();
 });

 test("downloads through the authenticated API client and preserves ordinary filenames",async()=>{
  const click=vi.fn();
  const appendChild=vi.spyOn(document.body,"appendChild").mockImplementation((node:any)=>node);
  vi.spyOn(document,"createElement").mockReturnValue({click,remove:vi.fn(),style:{},set href(_v:string){},set download(_v:string){}} as any);
  vi.stubGlobal("URL",{...URL,createObjectURL:vi.fn(()=>"blob:test"),revokeObjectURL:vi.fn()});
  const fetchMock=vi.fn().mockResolvedValue(new Response(new Blob(["abc"]),{status:200,headers:{"content-disposition":'attachment; filename="100% Design.pdf"'}}));
  vi.stubGlobal("fetch",fetchMock);
  const {downloadFile}=await import("./api");
  await expect(downloadFile("/export","fallback.csv")).resolves.toBe("100% Design.pdf");
  const headers=new Headers(fetchMock.mock.calls[0][1].headers);
  expect(headers.get("X-User-ID")).toBe("1");
  expect(click).toHaveBeenCalledOnce();
  appendChild.mockRestore();
 });

 test("decodes only RFC 5987 extended filenames",async()=>{
  vi.spyOn(document.body,"appendChild").mockImplementation((node:any)=>node);
  vi.spyOn(document,"createElement").mockReturnValue({click:vi.fn(),remove:vi.fn(),style:{},set href(_v:string){},set download(_v:string){}} as any);
  vi.stubGlobal("URL",{...URL,createObjectURL:vi.fn(()=>"blob:test"),revokeObjectURL:vi.fn()});
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(new Blob(["abc"]),{status:200,headers:{"content-disposition":"attachment; filename*=UTF-8''Budget%20Plan.pdf"}})));
  const {downloadFile}=await import("./api");
  await expect(downloadFile("/export","fallback.csv")).resolves.toBe("Budget Plan.pdf");
 });
});
