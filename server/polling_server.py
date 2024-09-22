import asyncio
import websockets
import json
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from websockets.exceptions import InvalidStatusCode

app = FastAPI()

# Global variable to store the order book data
order_books = {}

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Function to calculate the initial market price based on the order book
def calculate_initial_price(buy_orders, sell_orders):
    if not buy_orders and not sell_orders:
        return 0  # Return 0 if the order book is empty

    if buy_orders and not sell_orders:
        return max(buy_orders, key=lambda x: x['price'])['price']  # Use the highest bid as an estimate

    if sell_orders and not buy_orders:
        return min(sell_orders, key=lambda x: x['price'])['price']  # Use the lowest ask as an estimate

    # Calculate the midpoint price if both buy and sell orders exist
    best_bid = max(buy_orders, key=lambda x: x['price'])['price']
    best_ask = min(sell_orders, key=lambda x: x['price'])['price']
    
    if best_bid < best_ask:
        return (best_bid + best_ask) / 2  # Midpoint between best bid and best ask
    else:
        return 0  # If there's a logical error, fallback to 0 (shouldn't happen if correctly managed)

# Function to poll the WebSocket server for a specific ticker
async def poll_order_book(uri: str, ticker: str):
    try:
        async with websockets.connect(uri) as websocket:
            # Send a command to check the order book for the given ticker
            check_message = {
                "command": "check",
                "ticker": ticker
            }
            await websocket.send(json.dumps(check_message))
            response = await websocket.recv()
            order_book = json.loads(response)

            # Store the order book data
            order_books[ticker] = order_book

            # Calculate the initial price
            initial_price = calculate_initial_price(order_book['buy'], order_book['sell'])
            print(f"Updated order book for {ticker} with initial price {initial_price}: {order_book}")

            # You can choose to store this initial price or use it as needed
            order_books[ticker]['initial_price'] = initial_price

    except InvalidStatusCode as e:
        print(f"Failed to connect to WebSocket server: {e}")

# Background task to periodically poll the WebSocket server
async def poll_websocket_server():
    uri = "ws://localhost:8000/ws"  # The WebSocket server URI
    tickers = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'BRK.A', 'BRK.B', 'LLY', 'TSM', 'TSLA']

    while True:
        for ticker in tickers:
            await poll_order_book(uri, ticker)
        await asyncio.sleep(10)  # Poll every 10 seconds

@app.on_event("startup")
async def startup_event():
    # Start the background polling task when the server starts
    asyncio.create_task(poll_websocket_server())

@app.get("/", response_class=HTMLResponse)
async def get_order_book_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/order_books")
async def get_order_books():
    return order_books

@app.get("/order_books/{ticker}")
async def get_order_book_for_ticker(ticker: str):
    return order_books.get(ticker, {"error": "Ticker not found"})