from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ValidationError, model_validator, validator
import logging
import json
import time
from enum import Enum

app = FastAPI()

# Enums for order sides and types
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"

# Order model with validation
class Order(BaseModel):
    ticker: str
    side: OrderSide
    quantity: int
    user_id: str
    order_type: OrderType
    price: Optional[float] = None
    timestamp: float = Field(default_factory=time.time)

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive.')
        return v

    @model_validator(mode='after')
    def check_price(self):
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("Price is required for limit orders.")
        if self.order_type == OrderType.MARKET:
            self.price = None  # Ensure price is None for market orders
        return self

# OrderBook class to manage orders for a ticker
class OrderBook:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.buy_orders: List[Order] = []
        self.sell_orders: List[Order] = []

    def add_order(self, order: Order):
        if order.order_type == OrderType.MARKET:
            matched_orders = self.match_market_order(order)
            return matched_orders
        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                self.buy_orders.append(order)
            else:
                self.sell_orders.append(order)
            self.sort_order_book()
            matched_orders = self.match_limit_orders()
            return matched_orders
        else:
            raise ValueError("Invalid order type.")

    def sort_order_book(self):
        self.buy_orders.sort(key=lambda x: (-x.price if x.price else float('-inf'), x.timestamp))
        self.sell_orders.sort(key=lambda x: (x.price if x.price else float('inf'), x.timestamp))

    def match_market_order(self, order: Order):
        matched_orders = []
        quantity_to_match = order.quantity

        if order.side == OrderSide.BUY:
            order_list = self.sell_orders
        else:
            order_list = self.buy_orders

        while quantity_to_match > 0 and order_list:
            best_order = order_list[0]
            matched_quantity = min(quantity_to_match, best_order.quantity)
            matched_price = best_order.price
            matched_orders.append({
                'price': matched_price,
                'quantity': matched_quantity,
                'maker_user_id': best_order.user_id,
                'taker_user_id': order.user_id,
                'timestamp': time.time()
            })
            best_order.quantity -= matched_quantity
            quantity_to_match -= matched_quantity
            if best_order.quantity == 0:
                order_list.pop(0)

        if quantity_to_match > 0:
            logging.info(f"Order partially filled. Unmatched quantity: {quantity_to_match}")

        return matched_orders

    def match_limit_orders(self):
        matched_orders = []
        while self.buy_orders and self.sell_orders:
            best_buy = self.buy_orders[0]
            best_sell = self.sell_orders[0]

            if best_buy.price >= best_sell.price:
                matched_quantity = min(best_buy.quantity, best_sell.quantity)
                matched_price = best_sell.price
                matched_orders.append({
                    'price': matched_price,
                    'quantity': matched_quantity,
                    'buy_user_id': best_buy.user_id,
                    'sell_user_id': best_sell.user_id,
                    'timestamp': time.time()
                })
                best_buy.quantity -= matched_quantity
                best_sell.quantity -= matched_quantity
                if best_buy.quantity == 0:
                    self.buy_orders.pop(0)
                if best_sell.quantity == 0:
                    self.sell_orders.pop(0)
            else:
                break
        return matched_orders

    def get_order_book(self):
        return {
            'buy': [order.dict() for order in self.buy_orders],
            'sell': [order.dict() for order in self.sell_orders]
        }

# Manager to handle multiple order books
class OrderBookManager:
    def __init__(self):
        self.order_books: Dict[str, OrderBook] = {}

    def get_order_book(self, ticker: str) -> OrderBook:
        if ticker not in self.order_books:
            self.order_books[ticker] = OrderBook(ticker)
        return self.order_books[ticker]

    def add_order(self, order: Order):
        order_book = self.get_order_book(order.ticker)
        matched_orders = order_book.add_order(order)
        return matched_orders

    def list_tickers(self):
        return [ticker for ticker, ob in self.order_books.items() if ob.buy_orders or ob.sell_orders]

    def get_order_book_snapshot(self, ticker: str):
        order_book = self.get_order_book(ticker)
        return order_book.get_order_book()

order_book_manager = OrderBookManager()

# Connection manager to handle multiple WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# WebSocket endpoint to handle client connections and messages
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text("Error: Invalid JSON format.")
                continue

            command = message.get("command")
            if not command:
                await websocket.send_text("Error: Missing command.")
                continue

            if command == "add":
                order_data = message.get("order")
                if not order_data:
                    await websocket.send_text("Error: Missing order data.")
                    continue
                try:
                    order = Order(**order_data)
                except ValidationError as e:
                    await websocket.send_text(f"Error: Invalid order data. {e}")
                    continue

                matched_orders = order_book_manager.add_order(order)
                if matched_orders:
                    await manager.broadcast(json.dumps({"matched_orders": matched_orders}))
                else:
                    await websocket.send_text("Order added to the order book.")

            elif command == "check":
                ticker = message.get("ticker")
                if not ticker:
                    await websocket.send_text("Error: Missing ticker symbol.")
                    continue
                order_book_snapshot = order_book_manager.get_order_book_snapshot(ticker)
                await websocket.send_text(json.dumps(order_book_snapshot))

            elif command == "list_tickers":
                tickers = order_book_manager.list_tickers()
                await websocket.send_text(json.dumps({"tickers": tickers}))

            else:
                await websocket.send_text("Error: Invalid command.")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info("Client disconnected")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await websocket.send_text(f"Error: {str(e)}")
    finally:
        await websocket.close()