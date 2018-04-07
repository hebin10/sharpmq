#!/usr/bin/env python
import pika
import uuid
import ujson
from multiprocessing import Pool
import signal
import traceback
import sys


proc_num = 100
credentials = pika.PlainCredentials(username='guest', password='guest')
mq_info = {'host': '127.0.0.1', 'port': 5672, 'credentials': credentials}


class RPCClient(object):
    def __init__(self, index):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(**mq_info))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='to_mq2', exchange_type='topic')
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
        self.index = index

    def call(self):
        self.corr_id = str(uuid.uuid4())
        self.response = None
        body = {'_method': 'func', 'word': str(self.index)}
        body = ujson.dumps(body)
        self.channel.basic_publish(exchange='to_mq2',
                                   routing_key='compute.' + str(self.index),
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue_name,
                                       correlation_id=self.corr_id,
                                   ),
                                   body=body)
        while self.response is None:
            self.connection.process_data_events()
        return int(self.response)

    def cast(self):
        pass

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body


def signal_handler():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def callback(retvalue):
    print "Process return value is: %s" % str(retvalue)


def worker(index):
    # do some work with parameters.
    # when handling exceptions use `traceback` module
    # to print full traceback.
    # remember to handle exceptions properly, so that
    # the subprocess can exit gracefully.
    try:
        rpc_server = RPCClient(index)
        while True:
            sys.stdout.write(str(rpc_server.call()) + '\n\n')
    except Exception:
        traceback.print_exc()


def main():
    pool = Pool(proc_num, signal_handler)
    # when using pool, don't try to use multiprocessing.Queue()
    # queue = Manager().Queue()
    try:
        for i in range(proc_num):
            pool.apply_async(worker, args=(i,), callback=callback)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()


if __name__ == '__main__':
    main()