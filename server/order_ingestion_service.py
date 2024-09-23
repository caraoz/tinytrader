from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel, Field, ValidationError
from enum import Enum
import pika
import json
import logging

app = FastAPI()

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Enums for order sides and types
class OrderSide(str, Enum):
    buy = "buy"
    sell = "sell"

class OrderType(str, Enum):
    market = "market"
    limit = "limit"

# Pydantic model for order validation
class Order(BaseModel):
    ticker: str = Field(..., example="AAPL")
    side: OrderSide = Field(..., example="buy")
    quantity: int = Field(..., example=100, gt=0)
    user_id: str = Field(..., example="user123")
    order_type: OrderType = Field(..., example="limit")
    price: float = Field(None, example=150.0, gt=0)  # Only required for limit orders

# Function to get a connection to RabbitMQ
def get_rabbitmq_connection():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.exchange_declare(exchange='orders', exchange_type='direct')
        return connection, channel
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail="Could not connect to message broker")

# Function to publish order to RabbitMQ
def publish_order(connection, channel, order):
    try:
        channel.basic_publish(
            exchange='orders',
            routing_key='new_order',
            body=json.dumps(order.dict()),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
        logging.info(f" [x] Sent {order.dict()}")
    except Exception as e:
        logging.error(f"Failed to publish order: {e}")
    finally:
        channel.close()
        connection.close()

# API endpoint to submit orders
@app.post("/submit-order/")
async def submit_order(order: Order, background_tasks: BackgroundTasks):
    try:
        connection, channel = get_rabbitmq_connection()
        background_tasks.add_task(publish_order, connection, channel, order)
        return {"status": "Order submitted"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint for health check
@app.get("/")
def read_root():
    return {"message": "Order Ingestion Service is running"}

# Graceful shutdown to handle cleanup
@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down service...")
    # Here you could close other resources if necessary

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)