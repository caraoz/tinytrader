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
        channel.queue_declare(queue='notifications', durable=True)
        return connection, channel
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail="Could not connect to message broker")

# Function to send notifications
def send_notification(ch, method, properties, body):
    notification = json.loads(body)
    print(f" [x] Sending notification: {notification}")
    # Add logic to send notifications to users (e.g., via email or WebSocket)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start the notification service
def start_notification_service():
    try:
        connection, channel = get_rabbitmq_connection()
        channel.basic_consume(queue='notifications', on_message_callback=send_notification)
        print(' [*] Waiting to send notifications. To exit press CTRL+C')
        channel.start_consuming()
    except Exception as e:
        logging.error(f"Error in notification service: {e}")
    finally:
        try:
            channel.close()
            connection.close()
        except Exception as close_err:
            logging.error(f"Error closing RabbitMQ connection: {close_err}")

@app.get("/")
def read_root():
    return {"message": "Hello from Notification Service"}

# Graceful shutdown to handle cleanup
@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down Notification Service...")
    # Add any necessary cleanup logic here

if __name__ == "__main__":
    start_notification_service()