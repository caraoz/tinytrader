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
        channel.queue_declare(queue='matching_engine', durable=True)
        return connection, channel
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail="Could not connect to message broker")

# Function to process orders for matching
def match_order(ch, method, properties, body):
    order = json.loads(body)
    print(f" [x] Matching order: {order}")
    # Add logic to match orders here
    # If matched, send trade execution message
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start the matching engine service
def start_matching_engine_service():
    try:
        connection, channel = get_rabbitmq_connection()
        channel.basic_consume(queue='matching_engine', on_message_callback=match_order)
        print(' [*] Waiting to match orders. To exit press CTRL+C')
        channel.start_consuming()
    except Exception as e:
        logging.error(f"Error in matching engine service: {e}")
    finally:
        try:
            channel.close()
            connection.close()
        except Exception as close_err:
            logging.error(f"Error closing RabbitMQ connection: {close_err}")

@app.get("/")
def read_root():
    return {"message": "Hello from Matching Engine Service"}

# Graceful shutdown to handle cleanup
@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down Matching Engine Service...")
    # Add any necessary cleanup logic here

if __name__ == "__main__":
    start_matching_engine_service()