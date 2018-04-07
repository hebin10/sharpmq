#!/usr/bin/env python
import pika
import ujson
from multiprocessing import Pool
import signal
import traceback


proc_num = 1024
credentials = pika.PlainCredentials(username='stackrabbit',
                                    password='1234qwer')
mq_info = {'host': '127.0.0.1', 'port': 5672, 'credentials': credentials}


def default_func(*args, **kwargs):
    return 'm' * 1024


class RPCServer(object):
    def __init__(self, compute):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(**mq_info))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='shovel', exchange_type='topic')
        self.channel.exchange_declare(exchange='to_mq1', exchange_type='topic')
        self.queue = self.channel.queue_declare(queue=compute)
        self.channel.queue_bind(exchange='shovel', queue=compute,
                                routing_key=compute)

    def on_response(self, ch, method, props, body):
        try:
            payload = ujson.loads(body)
            _method = payload.get('_method', None)
            word = payload.get('word', 'm')
        except Exception:
            _method = None
            word = 'm'

        try:
            _method = getattr(self, _method)
        except Exception:
            _method = default_func

        response = _method(word)

        ch.basic_publish(exchange='to_mq1', routing_key=props.reply_to,
                         properties=pika.BasicProperties(
                             correlation_id=props.correlation_id),
                         body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    @staticmethod
    def func(word):
        return word * 1024

    def start(self):
        try:
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(self.on_response,
                                       queue=self.queue.method.queue)
            self.channel.start_consuming()
        except Exception:
            traceback.print_exc()


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
        rpc_server = RPCServer(compute='compute.' + str(index))
        rpc_server.start()
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
