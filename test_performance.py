import asyncio
import aiohttp
import time

async def fetch_predict(session, symbol):
    start = time.time()
    try:
        # Assuming the server is running on localhost:8000
        async with session.get(f'http://localhost:8000/predict/{symbol}?interval=1h&period=1mo', headers={'Authorization': 'Bearer test_token'}) as response:
            await response.read()
            return time.time() - start
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return time.time() - start

async def main():
    async with aiohttp.ClientSession() as session:
        # We will try to spam NIFTY endpoint
        tasks = [fetch_predict(session, 'NIFTY') for _ in range(20)]
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        print(f"Total time for 20 concurrent requests: {total_time:.2f}s")
        print(f"Average time per request: {sum(results)/len(results):.2f}s")
        print(f"Max time: {max(results):.2f}s")
        print(f"Min time: {min(results):.2f}s")

if __name__ == '__main__':
    asyncio.run(main())
