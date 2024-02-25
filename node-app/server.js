// @flow
const express = require('express');
const bodyParser = require('body-parser');
const { initTracer, TChannelBridge } = require('jaeger-client');
const amqp = require('amqplib/callback_api');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

app.use(bodyParser.json());

// Jaeger Tracer Configuration
const config = {
  serviceName: 'nodejs-api',
  sampler: {
    type: 'const',
    param: 1,
  },
  reporter: {
    logSpans: true,
    agentHost: process.env.JAEGER_AGENT_HOST || 'localhost',
    agentPort: process.env.JAEGER_AGENT_PORT || 5775,
  },
};
const options = {};
const tracer = initTracer(config, options);

// RabbitMQ Configuration
const rabbitUrl = process.env.RABBITMQ_URL || 'amqp://user:password@rabbitmq';

app.use((req, res, next) => {
  const span = tracer.startSpan(req.path);
  req.span = span;

  res.on('finish', () => {
    span.setTag('http.status_code', res.statusCode);
    span.finish();
  });

  next();
});

app.get('/publish', (req, res) => {
  const span = tracer.startSpan('publish_message', { childOf: req.span });
  try {
    publishMessage('Hello World!', span);
    res.send('Message sent to RabbitMQ from Node.js API with Jaeger Tracing!');
  } catch (error) {
    console.error(error);
    res.status(500).send('Failed to send message.');
  } finally {
    span.finish();
  }
});

app.post('/process', (req, res) => {
  const span = tracer.startSpan('process_post', { childOf: req.span });
  try {
    console.log('Processed data received:', req.body);
    res.status(200).send({ message: 'Data processed by Python worker received.' });
  } catch (error) {
    console.error(error);
    res.status(500).send('Failed to process data.');
  } finally {
    span.finish();
  }
});

app.get('/', (req, res) => {
  const span = tracer.startSpan('root_access', { childOf: req.span });
  res.status(200).send('Node.js API with Jaeger Tracing and RabbitMQ Integration is running.');
  span.finish();
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

function publishMessage(message, span) {
  amqp.connect(rabbitUrl, (error0, connection) => {
    if (error0) {
      span.setTag('error', true);
      span.log({ event: 'error_connecting_to_rabbitmq', 'error.object': error0 });
      throw error0;
    }
    connection.createChannel((error1, channel) => {
      if (error1) {
        span.setTag('error', true);
        span.log({ event: 'error_creating_channel', 'error.object': error1 });
        throw error1;
      }
      const queue = 'task_queue';
      channel.assertQueue(queue, { durable: true });
      channel.sendToQueue(queue, Buffer.from(message), { persistent: true });
      console.log(" [x] Sent '%s'", message);
      span.log({ event: 'message_published', value: message });

      setTimeout(() => {
        connection.close();
        span.finish();
      }, 500); // Close connection after message is sent
    });
  });
}
