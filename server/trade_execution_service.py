import pika
import json
import logging
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Function to get RabbitMQ connection
def get_rabbitmq_connection():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='trade_execution', durable=True)
        return connection, channel
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail="Could not connect to message broker")

# Function to process trade executions
def execute_trade(ch, method, properties, body):
    trade = json.loads(body)
    print(f" [x] Executing trade: {trade}")
    # Add logic to update user balances, etc.
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start the trade execution service
def start_trade_execution_service():
    try:
        connection, channel = get_rabbitmq_connection()
        channel.basic_consume(queue='trade_execution', on_message_callback=execute_trade)
        print(' [*] Waiting to execute trades. To exit press CTRL+C')
        channel.start_consuming()
    except Exception as e:
        logging.error(f"Error in trade execution service: {e}")
    finally:
        try:
            channel.close()
            connection.close()
        except Exception as close_err:
            logging.error(f"Error closing RabbitMQ connection: {close_err}")

@app.get("/")
def read_root():
    return {"message": "Hello from Trade Execution Service"}

# Graceful shutdown to handle cleanup
@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down Trade Execution Service...")
    # Add any necessary cleanup logic here

if __name__ == "__main__":
    start_trade_execution_service()