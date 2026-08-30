import {afterEach,beforeEach,describe,expect,test,vi} from "vitest";

vi.mock("@/services/auth",()=>({
 authMode:()=> "development_header",
 beginLogin:vi.fn(),
 getAccessToken:()=>null,
}));

describe("GAP-002 API request timeout and cancellation",()=>{
 beforeEach(()=>{vi.useFakeTimers()});
 afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks()});

 test("aborts an unresponsive request with a clear timeout error",async()=>{
  vi.stubGlobal("fetch",vi.fn((_url:RequestInfo|URL,init?:RequestInit)=>new Promise((_resolve,reject)=>{
   init?.signal?.addEventListener("abort",()=>reject(new DOMException("Aborted","AbortError")),{once:true});
  })));
  const {request}=await import("./api");
  const pending=request("/slow",{timeoutMs:25});
  await vi.advanceTimersByTimeAsync(25);
  await expect(pending).rejects.toThrow("did not respond within 1 seconds");
 });

 test("honours caller cancellation without reporting a timeout",async()=>{
  vi.stubGlobal("fetch",vi.fn((_url:RequestInfo|URL,init?:RequestInit)=>new Promise((_resolve,reject)=>{
   init?.signal?.addEventListener("abort",()=>reject(new DOMException("Aborted","AbortError")),{once:true});
  })));
  const {request}=await import("./api");
  const controller=new AbortController();
  const pending=request("/cancel",{signal:controller.signal,timeoutMs:5000});
  controller.abort();
  await expect(pending).rejects.toMatchObject({name:"AbortError"});
 });

 test("clears the timeout after a successful response",async()=>{
  const clearSpy=vi.spyOn(globalThis,"clearTimeout");
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify({ok:true}),{status:200,headers:{"Content-Type":"application/json"}})));
  const {request}=await import("./api");
  await expect(request<{ok:boolean}>("/ok",{timeoutMs:1000})).resolves.toEqual({ok:true});
  expect(clearSpy).toHaveBeenCalled();
 });
});
