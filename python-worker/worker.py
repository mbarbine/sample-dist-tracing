import json
import os
import requests
import pika
import time
from jaeger_client import Config
import logging
from contextlib import contextmanager
from logging.config import dictConfig
from opentracing.propagation import Format

# Configure structured logging
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# Configuration settings from environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password')
NODE_API_URL = os.getenv('NODE_API_URL', 'http://node-app:3000')
QUEUE_NAME = os.getenv('QUEUE_NAME', 'task_queue')

def initialize_tracer():
    """Initialize and return a Jaeger tracer."""
    config = Config(
        config={
            'sampler': {'type': 'const', 'param': 1},
            'logging': True,
        },
        service_name='python-worker',
    )
    return config.initialize_tracer()

@contextmanager
def rabbitmq_connection():
    """Yield a RabbitMQ connection, reconnecting on error."""
    connection = None
    while connection is None:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
            connection = pika.BlockingConnection(parameters)
            logging.info('Connected to RabbitMQ!')
            yield connection
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Error connecting to RabbitMQ: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def post_to_node_api(data, tracer, parent_span):
    """Post processed data to Node.js API with distributed tracing."""
    headers = {"Content-Type": "application/json"}
    # Inject the current span context into the headers to propagate the trace
    tracer.inject(parent_span.context, Format.HTTP_HEADERS, headers)
    
    with tracer.start_active_span('post_to_node_api', child_of=parent_span) as scope:
        try:
            response = requests.post(f"{NODE_API_URL}/process", data=json.dumps(data), headers=headers)
            scope.span.set_tag('http.status_code', response.status_code)
            logging.info(f"Posted to Node.js API /process, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            scope.span.set_tag('http.error', str(e))
            logging.error(f"Failed to post to Node.js API /process: {e}")

def process_message(body, tracer):
    """Process received message and post result to Node.js API."""
    with tracer.start_active_span('process_message') as scope:
        span = scope.span
        span.set_tag('processing.type', 'message_processing')
        data = {'original': body.decode(), 'processed': True}
        logging.info(f"Processing message: {data['original']}")
        post_to_node_api(data, tracer, span)

def callback(ch, method, properties, body, tracer):
    """Callback function for handling messages from RabbitMQ."""
    process_message(body, tracer)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    tracer = initialize_tracer()
    with rabbitmq_connection() as connection:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)
        on_message_callback = lambda ch, method, properties, body: callback(ch, method, properties, body, tracer)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message_callback)
        logging.info('Waiting for messages. To exit press CTRL+C')
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            connection.close()
            tracer.close()

if __name__ == "__main__":
    main()
