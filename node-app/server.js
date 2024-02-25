const express = require('express');
const bodyParser = require('body-parser');
const { initTracer } = require('jaeger-client');
const amqp = require('amqplib/callback_api');

const app = express();
const port = process.env.PORT || 3000;

// Middleware to parse JSON bodies
app.use(bodyParser.json());

// Jaeger Tracer Configuration
const config = {
  serviceName: 'nodejs-api',
  sampler: { type: 'const', param: 1 },
  reporter: {
    logSpans: true,
    agentHost: process.env.JAEGER_AGENT_HOST || 'jaeger',
    agentPort: process.env.JAEGER_AGENT_PORT || 6831,
  },
};
const options = {
  logger: {
    info(msg) { console.log('INFO ', msg); },
    error(msg) { console.error('ERROR', msg); },
  },
};
const tracer = initTracer(config, options);

// RabbitMQ Configuration
const rabbitUrl = process.env.RABBITMQ_URL || 'amqp://user:password@rabbitmq';

// Middleware for tracing each request
app.use((req, res, next) => {
  const span = tracer.startSpan(req.path);
  req.span = span;

  res.on('finish', () => {
    span.setTag('http.status_code', res.statusCode);
    span.finish();
  });

  next();
});

// Route to publish a message to RabbitMQ
app.get('/publish', (req, res) => {
  const span = req.span;
  span.log({event: 'request_received'});

  try {
    publishMessage('Hello World!', span);
    res.send('Message sent to RabbitMQ from Node.js API with Jaeger Tracing!');
  } catch (error) {
    console.error(error);
    res.status(500).send('Failed to send message.');
  } finally {
    span.log({event: 'request_end'});
    span.finish();
  }
});

// Route for the Python worker to post back
app.post('/process', (req, res) => {
  const span = tracer.startSpan('process_post');
  try {
    console.log('Processed data received:', req.body);
    res.status(200).send({ message: 'Data processed by Python worker received.' });
    span.log({event: 'data_received', value: req.body});
  } catch (error) {
    console.error(error);
    res.status(500).send('Failed to process data.');
    span.setTag('error', true);
    span.log({event: 'error_processing_data', 'error.object': error});
  } finally {
    span.finish();
  }
});

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

function publishMessage(message, span) {
  amqp.connect(rabbitUrl, (error0, connection) => {
    if (error0) {
      span.setTag('error', true);
      span.log({event: 'error_connecting_to_rabbitmq', 'error.object': error0});
      throw error0;
    }
    connection.createChannel((error1, channel) => {
      if (error1) {
        span.setTag('error', true);
        span.log({event: 'error_creating_channel', 'error.object': error1});
        throw error1;
      }
      const queue = 'task_queue';
      channel.assertQueue(queue, { durable: true });
      channel.sendToQueue(queue, Buffer.from(message), { persistent: true });
      console.log(" [x] Sent '%s'", message);
      span.log({event: 'message_published', value: message});

      setTimeout(() => {
        connection.close();
      }, 500); // Close connection after message is sent
    });
  });
}
