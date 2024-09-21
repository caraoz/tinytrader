import asyncio
import websockets
import json

async def send_order():
    uri = "ws://localhost:8000/ws"  # The WebSocket server URI
    async with websockets.connect(uri) as websocket:
        # Create the JSON message
        message = {
            "command": "list_tickers"
        }

        # Convert the dictionary to a JSON string
        message_json = json.dumps(message)

        # Send the JSON message to the server
        await websocket.send(message_json)
        print(f"Sent: {message_json}")

        # Wait for a response from the server
        response = await websocket.recv()
        print(f"Received: {response}")

# Run the WebSocket client
asyncio.get_event_loop().run_until_complete(send_order())