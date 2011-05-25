import random
import socket
import string
import sys
import time
import unittest2 as unittest
import warnings
import weakref

from nose import SkipTest

from kombu import BrokerConnection
from kombu import Producer, Consumer, Exchange, Queue
from kombu.tests.utils import skip_if_quick

if sys.version_info >= (2, 5):
    from hashlib import sha256 as _digest
else:
    from sha import new as _digest  # noqa


def say(msg):
    sys.stderr.write(unicode(msg) + "\n")


def consumeN(conn, consumer, n=1, timeout=30):
    messages = []

    def callback(message_data, message):
        messages.append(message_data)
        message.ack()

    prev, consumer.callbacks = consumer.callbacks, [callback]
    consumer.consume()

    seconds = 0
    while True:
        try:
            conn.drain_events(timeout=1)
        except socket.timeout:
            seconds += 1
            msg = "Received %s/%s messages. %s seconds passed." % (
                    len(messages), n, seconds)
            if seconds >= timeout:
                raise socket.timeout(msg)
            if seconds > 1:
                say(msg)
        if len(messages) >= n:
            break

    consumer.cancel()
    consumer.callback = prev
    return messages


class TransportCase(unittest.TestCase):
    transport = None
    prefix = None
    sep = '.'
    userid = None
    password = None
    event_loop_max = 100
    connection_options = {}
    suppress_disorder_warning = False

    connected = False
    skip_test_reason = None

    message_size_limit = None

    def before_connect(self):
        pass

    def after_connect(self, connection):
        pass

    def setUp(self):
        if self.transport:
            try:
                self.before_connect()
            except SkipTest, exc:
                self.skip_test_reason = str(exc)
            else:
                self.do_connect()
            self.exchange = Exchange(self.prefix, "direct")
            self.queue = Queue(self.prefix, self.exchange, self.prefix)

    def purge(self, names):
        chan = self.connection.channel()
        map(chan.queue_purge, names)

    def get_connection(self, **options):
        if self.userid:
            options.setdefault("userid", self.userid)
        if self.password:
            options.setdefault("password", self.password)
        return BrokerConnection(transport=self.transport, **options)

    def do_connect(self):
        self.connection = self.get_connection(**self.connection_options)
        try:
            self.connection.connect()
            self.after_connect(self.connection)
        except self.connection.connection_errors:
            self.skip_test_reason = "%s transport can't connect" % (
                                       self.transport, )
        else:
            self.connected = True

    def verify_alive(self):
        if self.transport:
            if not self.connected:
                raise SkipTest(self.skip_test_reason)
            return True

    def test_produce__consume(self):
        if not self.verify_alive():
            return
        chan1 = self.connection.channel()
        consumer = Consumer(chan1, self.queue)
        consumer.queues[0].purge()
        producer = Producer(chan1, self.exchange)
        producer.publish({"foo": "bar"}, routing_key=self.prefix)
        message = consumeN(self.connection, consumer)
        self.assertDictEqual(message[0], {"foo": "bar"})
        chan1.close()
        self.purge([self.queue.name])

    def _digest(self, data):
        return _digest(data).hexdigest()

    @skip_if_quick
    def test_produce__consume_large_messages(self, bytes=1048576, n=10,
            charset=string.punctuation + string.letters + string.digits):
        if not self.verify_alive():
            return
        bytes = min(filter(None, [bytes, self.message_size_limit]))
        messages = ["".join(random.choice(charset)
                        for j in xrange(bytes)) + "--%s" % n
                            for i in xrange(n)]
        digests = []
        chan1 = self.connection.channel()
        consumer = Consumer(chan1, self.queue)
        for queue in consumer.queues:
            queue.purge()
        producer = Producer(chan1, self.exchange)
        for i, message in enumerate(messages):
            producer.publish({"text": message,
                              "i": i}, routing_key=self.prefix)
            digests.append(self._digest(message))

        received = [(msg["i"], msg["text"])
                        for msg in consumeN(self.connection, consumer, n)]
        self.assertEqual(len(received), n)
        ordering = [i for i, _ in received]
        if ordering != range(n) and not self.suppress_disorder_warning:
            warnings.warn(
                "%s did not deliver messages in FIFO order: %r" % (
                    self.transport, ordering))

        for i, text in received:
            if text != messages[i]:
                raise AssertionError("%i: %r is not %r" % (
                    i, text[-100:], messages[i][-100:]))
            self.assertEqual(self._digest(text), digests[i])

        chan1.close()
        self.purge([self.queue.name])

    def P(self, rest):
        return "%s%s%s" % (self.prefix, self.sep, rest)

    def test_produce__consume_multiple(self):
        if not self.verify_alive():
            return
        chan1 = self.connection.channel()
        producer = Producer(chan1, self.exchange)
        b1 = Queue(self.P("b1"), self.exchange, "b1")(chan1)
        b2 = Queue(self.P("b2"), self.exchange, "b2")(chan1)
        b3 = Queue(self.P("b3"), self.exchange, "b3")(chan1)
        [q.declare() for q in (b1, b2, b3)]
        [q.purge() for q in (b1, b2, b3)]

        producer.publish("b1", routing_key="b1")
        producer.publish("b2", routing_key="b2")
        producer.publish("b3", routing_key="b3")
        chan1.close()

        chan2 = self.connection.channel()
        consumer = Consumer(chan2, [b1, b2, b3])
        messages = consumeN(self.connection, consumer, 3)
        self.assertItemsEqual(messages, ["b1", "b2", "b3"])
        chan2.close()
        self.purge([self.P("b1"), self.P("b2"), self.P("b3")])

    def test_timeout(self):
        if not self.verify_alive():
            return
        chan = self.connection.channel()
        self.purge([self.queue.name])
        consumer = Consumer(chan, self.queue)
        self.assertRaises(socket.timeout, self.connection.drain_events,
                timeout=0.3)
        consumer.cancel()

    def test_basic_get(self):
        if not self.verify_alive():
            return
        chan1 = self.connection.channel()
        producer = Producer(chan1, self.exchange)
        chan2 = self.connection.channel()
        queue = Queue(self.P("basic_get"), self.exchange, "basic_get")
        queue = queue(chan2)
        queue.declare()
        producer.publish({"basic.get": "this"}, routing_key="basic_get")
        chan1.close()

        for i in range(self.event_loop_max):
            m = queue.get()
            if m:
                break
            time.sleep(0.1)
        self.assertEqual(m.payload, {"basic.get": "this"})
        chan2.close()

    def test_cyclic_reference_transport(self):
        if not self.verify_alive():
            return

        def _createref():
            conn = self.get_connection()
            conn.transport
            conn.close()
            return weakref.ref(conn)

        self.assertIsNone(_createref()())

    def test_cyclic_reference_connection(self):
        if not self.verify_alive():
            return

        def _createref():
            conn = self.get_connection()
            conn.connect()
            conn.close()
            return weakref.ref(conn)

        self.assertIsNone(_createref()())

    def test_cyclic_reference_channel(self):
        if not self.verify_alive():
            return

        def _createref():
            conn = self.get_connection()
            conn.connect()
            channel = conn.channel()
            channel.close()
            conn.close()
            return weakref.ref(conn)

        self.assertIsNone(_createref()())

    def tearDown(self):
        if self.transport and self.connected:
            self.connection.close()
