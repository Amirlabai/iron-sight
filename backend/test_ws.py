import asyncio
import aiohttp
import json

async def test_ws():
    uri = "http://localhost:8080/ws"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(uri) as ws:
                print("Connected to WebSocket")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        print(f"Received message type: {data.get('type')}")
                        if data.get('type') == 'history_sync':
                            print(f"History length: {len(data.get('data', []))}")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print("WebSocket Error")
                        break
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(test_ws())
