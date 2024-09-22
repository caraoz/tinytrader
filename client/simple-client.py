import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

async def send_orders(orders, uri="ws://localhost:8000/ws"):
    try:
        async with websockets.connect(uri) as websocket:
            for order in orders:
                try:
                    # Construct the message with the command and order details
                    message = {
                        "command": "add",
                        "order": order
                    }

                    # Convert the message to a JSON string
                    message_json = json.dumps(message)

                    # Check if the connection is still open
                    if websocket.open:
                        # Send the order to the server
                        await websocket.send(message_json)
                        logging.info(f"Sent: {message_json}")

                        # Wait for a response from the server
                        response = await websocket.recv()
                        logging.info(f"Received: {response}")

                        # Add a short delay between orders
                        await asyncio.sleep(0.5)
                    else:
                        logging.error("Connection is closed, cannot send message.")
                        break

                except websockets.ConnectionClosed as e:
                    logging.error(f"WebSocket connection closed unexpectedly: {e}")
                    break

            logging.info("All orders sent, closing the connection.")

    except websockets.ConnectionClosedError as e:
        logging.error(f"Failed to connect or maintain the connection: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

# Define a list of orders to send
orders = [
    {
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 10,
        "user_id": "user123",
        "order_type": "limit",
        "price": 150  # Include price only for limit orders
    },
    {
        "ticker": "AAPL",
        "side": "sell",
        "quantity": 5,
        "user_id": "user456",
        "order_type": "limit",
        "price":450
    },
    {
        "ticker": "GOOG",
        "side": "buy",
        "quantity": 3,
        "user_id": "user789",
        "order_type": "limit",
        "price": 2700  # Include price only for limit orders
    },
    {
        "ticker": "GOOG",
        "side": "sell",
        "quantity": 4,
        "user_id": "user012",
        "order_type": "limit",
        "price":3300

    }
]

# Run the WebSocket client
asyncio.get_event_loop().run_until_complete(send_orders(orders))