import asyncio
import websockets
import csv
import json

async def send_orders(uri, orders):
    async with websockets.connect(uri) as websocket:
        for order in orders:
            # Convert order data to the required JSON format
            order_data = {
                "command": "add",
                "order": {
                    "ticker": order['ticker'],
                    "side": order['side'],
                    "price": int(order['price']),
                    "quantity": int(order['quantity']),
                    "user_id": order['user_id'],
                    "order_type": order['order_type']
                }
            }

            # Convert the order to a JSON string
            message_json = json.dumps(order_data)

            # Send the JSON message to the server
            await websocket.send(message_json)
            print(f"Sent: {message_json}")

            # Wait for a response from the server
            response = await websocket.recv()
            print(f"Received: {response}")

            # Add a short delay between orders to simulate a real scenario
            await asyncio.sleep(0.1)

# Function to read orders from CSV file
def read_orders_from_csv(file_path):
    orders = []
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            orders.append(row)
    return orders

# Main function
async def main():
    uri = "ws://localhost:8000/ws"  # The WebSocket server URI
    file_path = "100_orders.csv"    # Path to the CSV file

    # Read orders from the CSV file
    orders = read_orders_from_csv(file_path)

    # Send the orders to the server
    await send_orders(uri, orders)

# Run the WebSocket client
asyncio.run(main())