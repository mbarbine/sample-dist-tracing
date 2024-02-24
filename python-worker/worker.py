import json
import pika
import requests
import time
import logging
from jaeger_client import Config
from opentracing_instrumentation.request_context import get_current_span, span_in_context

# RabbitMQ configuration
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'user'
RABBITMQ_PASS = 'password'
NODE_API_URL = 'http://node-app:3000/process'

# Queue and API configuration
QUEUE_NAME = 'task_queue'
NODE_API_URL = 'http://node-app:3000/process'

def process_message(body, tracer):
    """Process received message and post result to Node.js API."""
    with tracer.start_active_span('process_message') as scope:
        span = scope.span
        span.set_tag('processing.type', 'message_processing')
        
        # Simulate processing
        print(f"Received: {body}")
        processed_data = {'original': body.decode(), 'processed': True}
        
        # Trace API request
        with tracer.start_active_span('post_to_api', child_of=span) as post_scope:
            try:
                response = requests.post(NODE_API_URL, json=processed_data)
                post_scope.span.set_tag('http.status_code', response.status_code)
                print(f"Posted to Node.js API, status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                post_scope.span.set_tag('http.error', str(e))
                print(f"Failed to post to Node.js API: {e}")

def callback(ch, method, properties, body, tracer):
    """Callback function for handling messages from RabbitMQ."""
    process_message(body, tracer)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def connect_to_rabbitmq():
    """Establish connection to RabbitMQ with retries."""
    connection = None
    while connection is None:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
            connection = pika.BlockingConnection(parameters)
            print('Connected to RabbitMQ!')
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Error connecting to RabbitMQ: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def initialize_tracer():
    """Initialize Jaeger tracer."""
    config = Config(
        config={
            'sampler': {'type': 'const', 'param': 1},
            'logging': True,
        },
        service_name='python-worker',
    )
    return config.initialize_tracer()

if __name__ == "__main__":
    tracer = initialize_tracer()
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    
    # Declare queue and start consuming messages
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=lambda ch, method, properties, body: callback(ch, method, properties, body, tracer))
    print('Waiting for messages. To exit, press CTRL+C')
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()
        tracer.close()
