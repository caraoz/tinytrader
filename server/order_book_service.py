# order_book_service.py

import pika
import json

# Function to get RabbitMQ connection
def get_rabbitmq_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='order_book', durable=True)
    return channel

# Function to process incoming orders
def process_order(ch, method, properties, body):
    order = json.loads(body)
    print(f" [x] Received order: {order}")
    # Here, add logic to update the order book
    # This could involve adding orders to an in-memory data structure
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start consuming from the RabbitMQ queue
def start_order_book_service():
    channel = get_rabbitmq_connection()
    channel.basic_consume(queue='order_book', on_message_callback=process_order)
    print(' [*] Waiting for orders. To exit press CTRL+C')
    channel.start_consuming()

@app.get("/")
def read_root():
    return {"message": "Hello from Order Book Engine Service"}



if __name__ == "__main__":
    start_order_book_service()