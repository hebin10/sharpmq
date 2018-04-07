#!/usr/bin/env python
import pika
import uuid
import random


class FibonacciRpcClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='10.96.3.75', port=18001))
        self.channel = self.connection.channel()
        self.exchange = self.channel.exchange_declare(exchange='to_mq2',
                                                      exchange_type='topic')
        self.callback_queue = self.channel.queue_declare(
            queue='reply_' + uuid.uuid4().hex, auto_delete=True)
        self.callback_queue_name = self.callback_queue.method.queue
        self.channel.queue_bind(exchange='shovel',
                                queue=self.callback_queue_name,
                                routing_key=self.callback_queue_name)
        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue_name)
        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.corr_id = str(uuid.uuid4())
        self.response = None
        self.channel.basic_publish(exchange='to_mq2',
                                   routing_key='compute.w.x.y.z',
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue_name,
                                       correlation_id=self.corr_id,
                                   ),
                                   body=str(n))
        while self.response is None:
            self.connection.process_data_events()
        return int(self.response)


fibonacci_rpc = FibonacciRpcClient()

while True:
    n = random.randint(1, 31)
    fibonacci_rpc.call(1)
