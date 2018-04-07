#!/usr/bin/env python
import pika

mq_info = {'host': '127.0.0.1', 'port': 5672}

connection = pika.BlockingConnection(pika.ConnectionParameters(**mq_info))

channel = connection.channel()

channel.exchange_declare(exchange='to_mq1', exchange_type='topic')
channel.exchange_declare(exchange='shovel', exchange_type='topic')

channel.queue_declare(queue='compute.w.x.y.z')

channel.queue_bind(exchange='shovel', queue='compute.w.x.y.z',
                   routing_key='compute.w.x.y.z')


def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)


def on_request(ch, method, props, body):
    n = int(body)
    response = fib(n)
    ch.basic_publish(
        exchange='to_mq1',
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue='compute.w.x.y.z')
channel.start_consuming()
