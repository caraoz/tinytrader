## clears book - gets active tickers sends buy/sell orders to clear the book at every price level and quantity

import asyncio
import websockets
import json

async def fetch_active_tickers():
    uri = "ws://localhost:8000/ws"  # The WebSocket server URI

    async with websockets.connect(uri) as websocket:
        # Request the list of all tickers with open order books
        list_tickers_message = {
            "command": "list_tickers"
        }

        # Send the request to get all tickers
        await websocket.send(json.dumps(list_tickers_message))
        tickers_response = await websocket.recv()
        tickers_data = json.loads(tickers_response)

        # Extract and return tickers
        return tickers_data.get("tickers", [])

async def fetch_order_book(ticker):
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Request the order book for a specific ticker
        check_message = {
            "command": "check",
            "ticker": ticker
        }

        # Send the request to fetch the order book
        await websocket.send(json.dumps(check_message))
        order_book_response = await websocket.recv()

        # Parse and return the order book
        return json.loads(order_book_response)

async def send_order(order, ticker):
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Send the order to the WebSocket server
        order_message = {
            "command": "add",
            "order": {
                "ticker": ticker,
                "side": order["side"],
                "quantity": order["quantity"],
                "user_id": "clear_bot",  # Arbitrary user ID
                "order_type": "market",  # Use market orders to clear the book
                "price": order["price"]
            }
        }

        await websocket.send(json.dumps(order_message))
        response = await websocket.recv()
        print(f"Order Sent: {order_message} | Response: {response}")

async def clear_order_book(ticker, order_book):
    # Send sell orders to match the buy orders in the book
    for buy_order in order_book["buy"]:
        order = {
            "side": "sell",
            "price": buy_order["price"],
            "quantity": buy_order["quantity"]
        }
        await send_order(order, ticker)

    # Send buy orders to match the sell orders in the book
    for sell_order in order_book["sell"]:
        order = {
            "side": "buy",
            "price": sell_order["price"],
            "quantity": sell_order["quantity"]
        }
        await send_order(order, ticker)

async def main():
    # Step 1: Fetch active tickers
    tickers = await fetch_active_tickers()
    print(f"Active Tickers: {tickers}")

    # Step 2: For each ticker, fetch the order book and clear it
    for ticker in tickers:
        order_book = await fetch_order_book(ticker)
        if order_book["buy"] or order_book["sell"]:
            print(f"Clearing order book for {ticker}: {order_book}")
            await clear_order_book(ticker, order_book)

# Run the main function
asyncio.run(main())