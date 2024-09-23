import sqlite3
import logging
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Function to initialize the database
def init_db():
    try:
        conn = sqlite3.connect('trading_system.db')
        c = conn.cursor()
        # Create tables
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        ticker TEXT, 
                        user_id TEXT, 
                        price REAL, 
                        quantity INTEGER, 
                        side TEXT, 
                        status TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        ticker TEXT, 
                        buyer_id TEXT, 
                        seller_id TEXT, 
                        price REAL, 
                        quantity INTEGER, 
                        timestamp TEXT
                    )''')
        conn.commit()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing database: {e}")
        raise HTTPException(status_code=500, detail="Database initialization failed.")
    finally:
        conn.close()

# Function to save an order to the database
def save_order(order):
    try:
        conn = sqlite3.connect('trading_system.db')
        c = conn.cursor()
        c.execute('''INSERT INTO orders (ticker, user_id, price, quantity, side, status) 
                     VALUES (?, ?, ?, ?, ?, ?)''', 
                  (order['ticker'], order['user_id'], order['price'], order['quantity'], order['side'], 'open'))
        conn.commit()
        logging.info(f"Order saved: {order}")
    except sqlite3.Error as e:
        logging.error(f"Error saving order: {e}")
        raise HTTPException(status_code=500, detail="Failed to save order.")
    finally:
        conn.close()

# Function to save a trade to the database
def save_trade(trade):
    try:
        conn = sqlite3.connect('trading_system.db')
        c = conn.cursor()
        c.execute('''INSERT INTO trades (ticker, buyer_id, seller_id, price, quantity, timestamp) 
                     VALUES (?, ?, ?, ?, ?, ?)''', 
                  (trade['ticker'], trade['buyer_id'], trade['seller_id'], trade['price'], trade['quantity'], trade['timestamp']))
        conn.commit()
        logging.info(f"Trade saved: {trade}")
    except sqlite3.Error as e:
        logging.error(f"Error saving trade: {e}")
        raise HTTPException(status_code=500, detail="Failed to save trade.")
    finally:
        conn.close()

# Initialize the database on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Root endpoint for health check
@app.get("/")
def read_root():
    return {"message": "Persistence Service is running"}

# Example endpoint to save an order (for testing purposes)
@app.post("/save-order/")
def api_save_order(order: dict):
    save_order(order)
    return {"status": "Order saved successfully"}

# Example endpoint to save a trade (for testing purposes)
@app.post("/save-trade/")
def api_save_trade(trade: dict):
    save_trade(trade)
    return {"status": "Trade saved successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)