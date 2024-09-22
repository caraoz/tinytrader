import asyncio
import websockets
import json

async def show_order_books():
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

        # Extract tickers
        tickers = tickers_data.get("tickers", [])

        # Fetch and display the order book for each ticker
        for ticker in tickers:
            print(f"Order Book for {ticker}:\n")
            check_message = {
                "command": "check",
                "ticker": ticker
            }

            # Send the request to fetch the order book for the current ticker
            await websocket.send(json.dumps(check_message))
            order_book_response = await websocket.recv()

            # Log the raw response for debugging
            print(f"Raw response for {ticker}: '{order_book_response}'")

            # Check if the response is empty
            if not order_book_response.strip():
                print(f"Warning: Received an empty response for ticker {ticker}.")
                continue

            try:
                order_book_data = json.loads(order_book_response)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON response for ticker {ticker}: {e}")
                continue

            # Extract and format the buy and sell sides
            buy_orders = order_book_data.get("buy", [])
            sell_orders = order_book_data.get("sell", [])

            # Determine the maximum number of rows to display
            max_len = max(len(buy_orders), len(sell_orders))

            # Print the header
            print(f"{'Buy Orders':<40} {'Sell Orders':<40}")
            print("-" * 80)

            # Print each row of buy and sell orders
            for i in range(max_len):
                buy_order = buy_orders[i] if i < len(buy_orders) else {}
                sell_order = sell_orders[i] if i < len(sell_orders) else {}

                buy_str = (
                    f"Price: {buy_order.get('price', ''):<10} "
                    f"Quantity: {buy_order.get('quantity', ''):<10} "
                    f"UserID: {buy_order.get('user_id', ''):<10}"
                ) if buy_order else ""

                sell_str = (
                    f"Price: {sell_order.get('price', ''):<10} "
                    f"Quantity: {sell_order.get('quantity', ''):<10} "
                    f"UserID: {sell_order.get('user_id', ''):<10}"
                ) if sell_order else ""

                print(f"{buy_str:<40} {sell_str:<40}")

            print("\n")  # Newline for separating tickers

# Run the WebSocket client
asyncio.run(show_order_books())