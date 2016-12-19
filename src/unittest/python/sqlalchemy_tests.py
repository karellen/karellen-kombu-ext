import os
import sys
from logging import shutdown
from logging.config import dictConfig
from unittest import TestCase
from unittest.mock import patch

os.environ['KOMBU_LOG_CONNECTION'] = "1"
os.environ['KOMBU_LOG_CHANNEL'] = "1"

from kombu import Connection

from karellen.kombu import register_transports, unregister_transports


class SqlAlchemyTests(TestCase):
    @classmethod
    def setUpClass(cls):

        register_transports()
        dictConfig({
            "version": 1,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "stream": sys.stdout
                }
            },
            "loggers": {
                "kombu_tests": {
                    "handlers": ["console"],
                    "level": "DEBUG",
                    "propagate": False
                },
                "kombu_tests.connection": {
                    "handlers": ["console"],
                    "level": "DEBUG",
                    "propagate": False
                }
            }
        })

    @classmethod
    def tearDownClass(cls):
        unregister_transports()
        shutdown()

    def test_url_parser(self):
        with patch('karellen.kombu.transport.sqlalchemy.Channel._open'):
            url = 'sqlalchemy+sqlite:///celerydb.sqlite'
            Connection(url).connect()

            url = 'sqla+sqlite:///celerydb.sqlite'
            Connection(url).connect()

            # Should prevent regression fixed by f187ccd
            url = 'sqlb+sqlite:///celerydb.sqlite'
            with self.assertRaises(KeyError):
                Connection(url).connect()

    def test_simple_queueing(self):
        conn = Connection('sqlalchemy+sqlite:///:memory:')
        conn.connect()
        try:
            channel = conn.channel()
            self.assertEqual(
                channel.queue_cls.__table__.name,
                'kombu_queue'
            )
            self.assertEqual(
                channel.message_cls.__table__.name,
                'kombu_message'
            )
            channel._put('celery', 'DATA_SIMPLE_QUEUEING')
            self.assertEqual(channel._get('celery'), 'DATA_SIMPLE_QUEUEING')
        finally:
            conn.release()

    def test_custom_table_names(self):
        self.skipTest("This test globally affects SQLAlchemy class_registry in models")
        conn = Connection('sqlalchemy+sqlite:///:memory:', transport_options={
            'queue_tablename': 'my_custom_queue',
            'message_tablename': 'my_custom_message'
        })
        conn.connect()
        try:
            channel = conn.channel()
            self.assertEqual(
                channel.queue_cls.__table__.name,
                'my_custom_queue'
            )
            self.assertEqual(
                channel.message_cls.__table__.name,
                'my_custom_message'
            )
            channel._put('celery', 'DATA_CUSTOM_TABLE_NAMES')
            self.assertEqual(channel._get('celery'), 'DATA_CUSTOM_TABLE_NAMES')
        finally:
            conn.release()

    def test_clone(self):
        hostname = 'sqlite:///celerydb.sqlite'
        x = Connection('+'.join(['sqla', hostname]))
        try:
            self.assertEqual(x.uri_prefix, 'sqla')
            self.assertEqual(x.hostname, hostname)
            clone = x.clone()
            try:
                self.assertEqual(clone.hostname, hostname)
                self.assertEqual(clone.uri_prefix, 'sqla')
            finally:
                clone.release()
        finally:
            x.release()
