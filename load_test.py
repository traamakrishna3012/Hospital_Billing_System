
import asyncio
import httpx
import time
import statistics

BASE_URL = "https://hospital-billing-system.up.railway.app"
ENDPOINTS = ["/", "/health", "/api/v1/auth/me"]

async def fetch(client, url):
    start = time.perf_counter()
    try:
        response = await client.get(url)
        end = time.perf_counter()
        return response.status_code, end - start
    except Exception as e:
        return 0, 0

async def run_test(name, concurrency, requests_per_worker):
    print(f"\n--- Running Test: {name} ---")
    print(f"Concurrency: {concurrency}, Total Requests: {concurrency * requests_per_worker}")
    
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = []
        for _ in range(concurrency):
            for _ in range(requests_per_worker):
                tasks.append(fetch(client, f"{BASE_URL}/health"))
        
        start_time = time.perf_counter()
        raw_results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
    
    total_time = end_time - start_time
    status_codes = [r[0] for r in raw_results]
    latencies = [r[1] for r in raw_results if r[0] == 200]
    
    success_rate = (status_codes.count(200) / len(status_codes)) * 100
    
    print(f"Total Time: {total_time:.2f}s")
    print(f"Requests/sec: {len(status_codes) / total_time:.2f}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if latencies:
        print(f"Latency: Avg {statistics.mean(latencies)*1000:.1f}ms, "
              f"P95 {statistics.quantiles(latencies, n=20)[18]*1000:.1f}ms, "
              f"Max {max(latencies)*1000:.1f}ms")
    else:
        print("No successful requests to measure latency.")

async def main():
    # 1. Baseline
    await run_test("Baseline", 1, 5)
    
    # 2. Medium Load
    await run_test("Medium Load", 10, 10)
    
    # 3. High Load
    await run_test("High Load (Capacity Test)", 25, 10)

if __name__ == "__main__":
    asyncio.run(main())
