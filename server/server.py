import os
import json
import time
import logging
import asyncio
from enum import Enum
from typing import List, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError, model_validator, validator
import aiosqlite

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

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
    def __init__(self, ticker: str, db_path: str):
        self.ticker = ticker
        self.buy_orders: List[Order] = []
        self.sell_orders: List[Order] = []
        self.lock = asyncio.Lock()  # Ensure thread-safe operations
        self.db_path = db_path

    async def initialize_db(self):
        """
        Initialize the cleared_trades table if it doesn't exist.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cleared_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    cleared_at TEXT NOT NULL,
                    filler_user_id TEXT NOT NULL,
                    filled_user_id TEXT NOT NULL
                )
            ''')
            await db.commit()
        logging.info(f"Database initialized for ticker: {self.ticker}")

    async def _persist_cleared_trade(self, order_type: str, price: float, quantity: int, filler_user_id: str, filled_user_id: str):
        """
        Persists a cleared trade to the SQLite database.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO cleared_trades (ticker, order_type, price, quantity, cleared_at, filler_user_id, filled_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.ticker,
                order_type,
                price,
                quantity,
                time.strftime('%Y-%m-%d %H:%M:%S'),
                filler_user_id,
                filled_user_id
            ))
            await db.commit()
        logging.debug(f"Persisted cleared trade: {order_type}, {price}, {quantity}, {filler_user_id}, {filled_user_id}")

    async def add_order(self, order: Order):
        async with self.lock:
            logging.info(f"Adding order: {order}")
            if order.order_type == OrderType.MARKET:
                matched_orders = await self.match_market_order(order)
            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY:
                    self.buy_orders.append(order)
                else:
                    self.sell_orders.append(order)
                self.sort_order_book()
                matched_orders = await self.match_limit_orders()
            else:
                raise ValueError("Invalid order type.")
            await self._self_check(matched_orders)
            return matched_orders

    def sort_order_book(self):
        self.buy_orders.sort(key=lambda x: (-x.price if x.price else float('-inf'), x.timestamp))
        self.sell_orders.sort(key=lambda x: (x.price if x.price else float('inf'), x.timestamp))
        logging.debug(f"Sorted order book for {self.ticker}")

    async def match_market_order(self, order: Order):
        matched_orders = []
        quantity_to_match = order.quantity

        order_list = self.sell_orders if order.side == OrderSide.BUY else self.buy_orders

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

            # Persist the matched trade
            await self._persist_cleared_trade(
                order_type=order.side.value, 
                price=matched_price, 
                quantity=matched_quantity, 
                filler_user_id=order.user_id, 
                filled_user_id=best_order.user_id
            )

            logging.info(f"Matched {matched_quantity} units at {matched_price} between {order.user_id} and {best_order.user_id}")

            best_order.quantity -= matched_quantity
            quantity_to_match -= matched_quantity

            if best_order.quantity == 0:
                order_list.pop(0)
                logging.debug(f"Removed fully matched order: {best_order}")

        if quantity_to_match > 0:
            logging.info(f"Order partially filled. Unmatched quantity: {quantity_to_match}")

        return matched_orders

    async def match_limit_orders(self):
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

                # Persist the matched trade
                await self._persist_cleared_trade(
                    order_type="buy", 
                    price=matched_price, 
                    quantity=matched_quantity, 
                    filler_user_id=best_buy.user_id, 
                    filled_user_id=best_sell.user_id
                )

                logging.info(f"Matched {matched_quantity} units at {matched_price} between {best_buy.user_id} and {best_sell.user_id}")

                best_buy.quantity -= matched_quantity
                best_sell.quantity -= matched_quantity

                if best_buy.quantity == 0:
                    self.buy_orders.pop(0)
                    logging.debug(f"Removed fully matched buy order: {best_buy}")
                if best_sell.quantity == 0:
                    self.sell_orders.pop(0)
                    logging.debug(f"Removed fully matched sell order: {best_sell}")
            else:
                break
        return matched_orders

    async def _self_check(self, matched_orders: List[Dict]):
        """
        Self-checking method to verify that matched orders were persisted correctly.
        """
        async with aiosqlite.connect(self.db_path) as db:
            for matched_order in matched_orders:
                query = '''
                    SELECT * FROM cleared_trades 
                    WHERE ticker=? AND price=? AND quantity=? 
                    AND filler_user_id=? AND filled_user_id=?
                '''
                params = (
                    self.ticker,
                    matched_order['price'],
                    matched_order['quantity'],
                    matched_order.get('buy_user_id', matched_order.get('filler_user_id')),
                    matched_order.get('sell_user_id', matched_order.get('filled_user_id'))
                )
                async with db.execute(query, params) as cursor:
                    result = await cursor.fetchone()
                    if not result:
                        logging.error(f"Self-check failed: Matched order not persisted: {matched_order}")

    def get_order_book(self):
        return {
            'buy': [order.dict() for order in self.buy_orders],
            'sell': [order.dict() for order in self.sell_orders]
        }

# Manager to handle multiple order books
class OrderBookManager:
    def __init__(self, db_name: str = 'data.db'):
        self.order_books: Dict[str, OrderBook] = {}
        self.lock = asyncio.Lock()  # Protect the order_books dictionary
        self.db_name = db_name
        self.db_path = self._get_db_path()

    def _get_db_path(self) -> str:
        """
        Determines the path to the SQLite database.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, self.db_name)
        return db_path

    async def initialize_order_book(self, ticker: str):
        async with self.lock:
            if ticker not in self.order_books:
                order_book = OrderBook(ticker, self.db_path)
                await order_book.initialize_db()
                self.order_books[ticker] = order_book
                logging.info(f"Initialized order book for ticker: {ticker}")

    async def get_order_book(self, ticker: str) -> OrderBook:
        await self.initialize_order_book(ticker)
        return self.order_books[ticker]

    async def add_order(self, order: Order):
        order_book = await self.get_order_book(order.ticker)
        matched_orders = await order_book.add_order(order)
        return matched_orders

    async def list_tickers(self):
        async with self.lock:
            active_tickers = [ticker for ticker, ob in self.order_books.items() if ob.buy_orders or ob.sell_orders]
            logging.debug(f"Listing tickers: {active_tickers}")
            return active_tickers

    async def get_order_book_snapshot(self, ticker: str):
        order_book = await self.get_order_book(ticker)
        async with order_book.lock:
            snapshot = order_book.get_order_book()
            logging.debug(f"Order book snapshot for {ticker}: {snapshot}")
            return snapshot

order_book_manager = OrderBookManager()

# Connection manager to handle multiple WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()  # Protect the active_connections list

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
            logging.info(f"New client connected: {websocket.client}")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logging.info(f"Client disconnected: {websocket.client}")

    async def broadcast(self, message: str):
        async with self.lock:
            if not self.active_connections:
                logging.debug("No active connections to broadcast.")
                return
            logging.info(f"Broadcasting message to {len(self.active_connections)} clients.")
            await asyncio.gather(*[self._safe_send(connection, message) for connection in self.active_connections])

    async def _safe_send(self, connection: WebSocket, message: str):
        try:
            await connection.send_text(message)
        except Exception as e:
            logging.error(f"Failed to send message to {connection.client}: {e}")
            await self.disconnect(connection)

manager = ConnectionManager()

# WebSocket endpoint to handle client connections and messages
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    async def safe_send_text(websocket: WebSocket, message: str):
        try:
            if websocket.client_state.value != "connected":
                logging.warning(f"Attempt to send message on closed connection to {websocket.client}")
                return
            await websocket.send_text(message)
        except WebSocketDisconnect:
            logging.warning(f"WebSocket disconnected unexpectedly: {websocket.client}")
            await manager.disconnect(websocket)
        except Exception as e:
            logging.error(f"Failed to send message to {websocket.client}: {e}")
            await manager.disconnect(websocket)

    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                logging.debug(f"Received message: {message}")
            except json.JSONDecodeError:
                error_msg = "Error: Invalid JSON format."
                await safe_send_text(websocket, error_msg)
                logging.warning(f"Invalid JSON received from {websocket.client}")
                continue
            except WebSocketDisconnect:
                logging.info(f"Client {websocket.client} disconnected.")
                break  # Exit the loop if the client disconnects
            except Exception as e:
                error_msg = f"Error receiving data: {str(e)}"
                await safe_send_text(websocket, error_msg)
                logging.error(f"Error receiving data from {websocket.client}: {e}")
                continue

            command = message.get("command")
            if not command:
                error_msg = "Error: Missing command."
                await safe_send_text(websocket, error_msg)
                logging.warning(f"Missing command in message from {websocket.client}")
                continue

            if command == "add":
                order_data = message.get("order")
                if not order_data:
                    error_msg = "Error: Missing order data."
                    await safe_send_text(websocket, error_msg)
                    logging.warning(f"Missing order data in 'add' command from {websocket.client}")
                    continue
                try:
                    order = Order(**order_data)
                    logging.info(f"Adding order: {order}")
                except ValidationError as e:
                    error_details = e.errors()
                    error_msg = f"Error: Invalid order data. {error_details}"
                    await safe_send_text(websocket, error_msg)
                    logging.warning(f"Validation error for order data from {websocket.client}: {error_details}")
                    continue

                try:
                    matched_orders = await order_book_manager.add_order(order)
                    if matched_orders:
                        broadcast_msg = json.dumps({"matched_orders": matched_orders})
                        await manager.broadcast(broadcast_msg)
                        logging.info(f"Broadcasted matched orders for ticker {order.ticker}")
                    else:
                        success_msg = "Order added to the order book."
                        await safe_send_text(websocket, success_msg)
                        logging.info(f"Order added to the book without matches for ticker {order.ticker}")
                except Exception as e:
                    error_msg = f"Error processing order: {str(e)}"
                    await safe_send_text(websocket, error_msg)
                    logging.error(f"Error processing order from {websocket.client}: {e}")

            elif command == "check":
                ticker = message.get("ticker")
                if not ticker:
                    error_msg = "Error: Missing ticker symbol."
                    await safe_send_text(websocket, error_msg)
                    logging.warning(f"Missing ticker symbol in 'check' command from {websocket.client}")
                    continue
                try:
                    order_book_snapshot = await order_book_manager.get_order_book_snapshot(ticker)
                    await safe_send_text(websocket, json.dumps(order_book_snapshot))
                    logging.info(f"Sent order book snapshot for ticker {ticker} to {websocket.client}")
                except Exception as e:
                    error_msg = f"Error retrieving order book: {str(e)}"
                    await safe_send_text(websocket, error_msg)
                    logging.error(f"Error retrieving order book for {ticker}: {e}")

            elif command == "list_tickers":
                try:
                    tickers = await order_book_manager.list_tickers()
                    await safe_send_text(websocket, json.dumps({"tickers": tickers}))
                    logging.info(f"Sent list of tickers to {websocket.client}")
                except Exception as e:
                    error_msg = f"Error listing tickers: {str(e)}"
                    await safe_send_text(websocket, error_msg)
                    logging.error(f"Error listing tickers: {e}")

            else:
                error_msg = "Error: Invalid command."
                await safe_send_text(websocket, error_msg)
                logging.warning(f"Invalid command received from {websocket.client}: {command}")

    except WebSocketDisconnect:
        logging.info(f"Client {websocket.client} disconnected.")
    except Exception as e:
        logging.error(f"Unexpected error with {websocket.client}: {e}")
        await safe_send_text(websocket, f"Error: {str(e)}")
    finally:
        await manager.disconnect(websocket)
        # Ensure the WebSocket is closed only if it's still open
        if websocket.client_state.value == "connected":
            await websocket.close()