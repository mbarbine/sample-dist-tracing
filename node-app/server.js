const express = require('express');
const { initTracer } = require('jaeger-client');
const amqp = require('amqplib/callback_api');

const app = express();
const port = 3000;

// Jaeger Tracer Configuration
const config = {
  serviceName: 'nodejs-api',
  sampler: {
    type: 'const',
    param: 1,
  },
  reporter: {
    logSpans: true,
    agentHost: 'jaeger',
    agentPort: 6831,
  },
};
const options = {
  logger: {
    info(msg) {
      console.log('INFO ', msg);
    },
    error(msg) {
      console.error('ERROR', msg);
    },
  },
};
const tracer = initTracer(config, options);

// RabbitMQ Configuration
const rabbitUrl = 'amqp://user:password@rabbitmq';

function publishMessage(message, span) {
  amqp.connect(rabbitUrl, (error0, connection) => {
    if (error0) {
      throw error0;
    }
    connection.createChannel((error1, channel) => {
      if (error1) {
        throw error1;
      }
      const queue = 'task_queue';

      channel.assertQueue(queue, {
        durable: true,
      });
      channel.sendToQueue(queue, Buffer.from(message), {
        persistent: true,
      });

      console.log(" [x] Sent '%s'", message);
      span.log({event: 'message_published', value: message});

      setTimeout(() => {
        connection.close();
      }, 500); // Close connection after message is sent
    });
  });
}

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

// Route that publishes a message to RabbitMQ
app.get('/', async (req, res) => {
  const span = req.span;
  span.log({event: 'request_received'});

  publishMessage('Hello World!', span);

  res.send('Message sent to RabbitMQ from Node.js API with Jaeger Tracing!');
  span.log({event: 'request_end'});
  span.finish();
});

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
