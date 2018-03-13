import asyncio
import websockets

async def hello():
  async with websockets.connect('ws://localhost:5052') as websocket:
    name = input("Command >>> ")
    await websocket.send(name)
    print("> {}".format(name))

    greeting = await websocket.recv()
    print("< {}".format(greeting))

asyncio.get_event_loop().run_until_complete(hello())

