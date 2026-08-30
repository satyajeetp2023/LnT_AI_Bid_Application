import asyncio
import os
import statistics
import time

import httpx


BASE=os.getenv("PERF_BASE_URL","http://127.0.0.1:8000/api/v1")
HEADERS={"X-User-ID":"1"}
REQUESTS=int(os.getenv("PERF_REQUESTS","120"))
CONCURRENCY=int(os.getenv("PERF_CONCURRENCY","12"))
P95_LIMIT_MS=float(os.getenv("PERF_P95_MS","750"))
ERROR_RATE_LIMIT=float(os.getenv("PERF_ERROR_RATE","0.02"))


async def one(client,path):
    start=time.perf_counter()
    try:
        response=await client.get(BASE+path,headers=HEADERS,timeout=10)
        ok=200<=response.status_code<300
        return (time.perf_counter()-start)*1000,ok,response.status_code
    except Exception:
        return (time.perf_counter()-start)*1000,False,0


async def main():
    paths=["/health","/bids","/dashboard/summary","/historical-bids/intelligence"]
    sem=asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient() as client:
        async def task(i):
            async with sem:
                return await one(client,paths[i%len(paths)])
        results=await asyncio.gather(*(task(i) for i in range(REQUESTS)))

    latencies=[x[0] for x in results]
    failures=[x for x in results if not x[1]]
    p95=statistics.quantiles(latencies,n=100,method="inclusive")[94] if len(latencies)>=2 else latencies[0]
    error_rate=len(failures)/len(results)

    print(f"requests={len(results)} concurrency={CONCURRENCY} p95_ms={p95:.1f} error_rate={error_rate:.4f}")
    if failures:
        counts={}
        for _,_,status in failures:counts[status]=counts.get(status,0)+1
        print(f"failure_statuses={counts}")

    assert error_rate<=ERROR_RATE_LIMIT,f"error rate {error_rate:.4f} exceeds {ERROR_RATE_LIMIT:.4f}"
    assert p95<=P95_LIMIT_MS,f"p95 {p95:.1f} ms exceeds {P95_LIMIT_MS:.1f} ms"


if __name__=="__main__":
    asyncio.run(main())
