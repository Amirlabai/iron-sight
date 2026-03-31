import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_relay():
    url = os.getenv("RELAY_URL")
    key = os.getenv("RELAY_AUTH_KEY")
    print(f"Testing Relay: {url}")
    headers = {"x-relay-auth": key}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                print(f"Data: {text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_relay())
