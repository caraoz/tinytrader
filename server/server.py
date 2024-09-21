from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Tuple
import json

app = FastAPI()

# A simple in-memory order book that supports multiple tickers
order_books: Dict[str, Dict[str, List[Tuple[float, int]]]] = {}

# Initialize an order book for a given ticker
def initialize_order_book(ticker: str):
    if ticker not in order_books:
        order_books[ticker] = {
            "buy": [],  # List of tuples (price, quantity)
            "sell": []  # List of tuples (price, quantity)
        }

# A simple function to match orders for a given ticker
def match_orders(ticker: str):
    order_book = order_books[ticker]
    
    while order_book["buy"] and order_book["sell"]:
        best_buy = order_book["buy"][0]
        best_sell = order_book["sell"][0]

        if best_buy[0] >= best_sell[0]:
            # Match found
            quantity = min(best_buy[1], best_sell[1])
            print(f"Matched {quantity} units of {ticker} at price {best_sell[0]}")
            best_buy = (best_buy[0], best_buy[1] - quantity)
            best_sell = (best_sell[0], best_sell[1] - quantity)

            if best_buy[1] == 0:
                order_book["buy"].pop(0)
            else:
                order_book["buy"][0] = best_buy

            if best_sell[1] == 0:
                order_book["sell"].pop(0)
            else:
                order_book["sell"][0] = best_sell
        else:
            break

# Function to sort the order book for a given ticker
def sort_order_book(ticker: str):
    order_book = order_books[ticker]
    order_book["buy"].sort(key=lambda x: -x[0])  # Sort descending by price
    order_book["sell"].sort(key=lambda x: x[0])  # Sort ascending by price

# Handle adding an order
async def handle_add_order(message: Dict, websocket: WebSocket):
    ticker = message.get("ticker")
    order_type = message.get("type")
    price = message.get("price")
    quantity = message.get("quantity")

    if None in (ticker, order_type, price, quantity):
        await websocket.send_text("Error: Missing required fields.")
        return

    initialize_order_book(ticker)
    order_books[ticker][order_type].append((price, quantity))
    sort_order_book(ticker)
    match_orders(ticker)
    await manager.send_message(f"Order book for {ticker} updated: {order_books[ticker]}")

# Handle checking the order book
async def handle_check_order_book(message: Dict, websocket: WebSocket):
    ticker = message.get("ticker")

    if not ticker:
        await websocket.send_text("Error: Missing ticker symbol.")
        return

    if ticker in order_books:
        await websocket.send_text(f"Current order book for {ticker}: {order_books[ticker]}")
    else:
        await websocket.send_text(f"No order book found for {ticker}")

# Function to list all tickers with open order books
async def handle_list_tickers(websocket: WebSocket):
    tickers_with_orders = [ticker for ticker, orders in order_books.items() if orders["buy"] or orders["sell"]]
    if tickers_with_orders:
        await websocket.send_text(json.dumps({"tickers": tickers_with_orders}))
    else:
        await websocket.send_text("No tickers with open order books.")

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            command = message.get("command")

            if command == "add":
                await handle_add_order(message, websocket)
            elif command == "check":
                ticker = message.get("ticker")
                await process_check_request(ticker, websocket)
            elif command == "list_tickers":
                await handle_list_tickers(websocket)
            else:
                await websocket.send_text("Error: Invalid command")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.send_message("Client disconnected")