"""Kombu transport using the Django database as a message store."""
from __future__ import absolute_import, unicode_literals

import socket
import weakref
from threading import Event
from time import sleep

from django.conf import settings
from django.core import exceptions as errors
from kombu.five import Empty, monotonic
from kombu.transport import virtual
from kombu.utils import cached_property, symbol_by_name
from kombu.utils.encoding import bytes_to_str
from kombu.utils.json import loads, dumps

try:
    from django.apps import AppConfig
except ImportError:  # pragma: no cover
    pass
else:
    class KombuAppConfig(AppConfig):
        name = 'karellen.kombu.transport.django'
        label = name.replace('.', '_')
        verbose_name = 'Message queue'


    default_app_config = 'karellen.kombu.transport.django.KombuAppConfig'

VERSION = (1, 0, 0)
__version__ = '.'.join(map(str, VERSION))

try:
    POLLING_INTERVAL = getattr(settings, 'KOMBU_POLLING_INTERVAL',
                               getattr(settings, 'DJKOMBU_POLLING_INTERVAL', 5.0))
    from django.db import connection
except errors.ImproperlyConfigured:
    POLLING_INTERVAL = 5.0
    settings.configure()

TRANSPORT_NOTIFIERS = weakref.WeakKeyDictionary()


class Channel(virtual.Channel):
    queue_model = 'karellen.kombu.transport.django.models:Queue'

    def _new_queue(self, queue, **kwargs):
        self.Queue.objects.get_or_create(name=queue)

    def _put(self, queue, message, **kwargs):
        self.Queue.objects.publish(queue, dumps(message))

    def basic_consume(self, queue, *args, **kwargs):
        qinfo = self.state.queue_bindings(queue)
        exchange = next(qinfo)
        if self.typeof(exchange).type == 'fanout':
            return
        super(Channel, self).basic_consume(queue, *args, **kwargs)

    def _get(self, queue):
        m = self.Queue.objects.fetch(queue)
        if m:
            return loads(bytes_to_str(m))
        raise Empty()

    def _size(self, queue):
        return self.Queue.objects.size(queue)

    def _purge(self, queue):
        return self.Queue.objects.purge(queue)

    def refresh_connection(self):
        from django import db
        db.close_connection()

    @cached_property
    def Queue(self):
        return symbol_by_name(self.queue_model)


class Transport(virtual.Transport):
    Channel = Channel

    default_port = 0
    polling_interval = POLLING_INTERVAL
    channel_errors = (
        virtual.Transport.channel_errors + (
            errors.ObjectDoesNotExist, errors.MultipleObjectsReturned)
    )
    driver_type = 'sql'
    driver_name = 'django'

    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        TRANSPORT_NOTIFIERS[self] = Event()
        self.shutdown = False

    def driver_version(self):
        import django
        return '.'.join(map(str, django.VERSION))

    def drain_events(self, connection, timeout=None):
        time_start = monotonic()
        get = self.cycle.get
        polling_interval = self.polling_interval
        if timeout and polling_interval and polling_interval > timeout:
            polling_interval = timeout
        consume_pending = False  # We know there is a message to consume because we've been
        while 1:
            try:
                get(self._deliver, timeout=timeout)
                consume_pending = False
            except Empty:
                if self.shutdown or (timeout is not None and monotonic() - time_start >= timeout):
                    raise socket.timeout()
                if consume_pending:
                    sleep(0.000001)
                elif polling_interval is not None:
                    notifier = TRANSPORT_NOTIFIERS[self]
                    was_notified = notifier.wait(polling_interval)
                    if not was_notified and timeout is not None and monotonic() - time_start >= timeout:
                        raise socket.timeout()
                    notifier.clear()
                    consume_pending = True
                    sleep(0.000001)
            else:
                break

    def close_connection(self, connection):
        super().close_connection(connection)
        notifier = TRANSPORT_NOTIFIERS[self]
        notifier.set()


try:
    from karellen.sqlite3 import UpdateHookOps
    from django.db.backends.signals import connection_created
except:
    UpdateHookOps = None

if UpdateHookOps:
    UPDATE_OPS = {UpdateHookOps.SQLITE_INSERT}  # , UpdateHookOps.SQLITE_UPDATE}

    CONNECTION_DATA_PENDING = weakref.WeakKeyDictionary()


    def notify_all_transports(shutdown=False):
        for transport, notifier in list(TRANSPORT_NOTIFIERS.items()):
            transport.shutdown = shutdown
            notifier.set()


    class SqliteMessageExistsNotification:
        def __init__(self):
            self.message_table_name = None

        def rollback_hook(self, conn):
            CONNECTION_DATA_PENDING[conn] = False

        def commit_hook(self, conn):
            data_pending = CONNECTION_DATA_PENDING.get(conn)
            if data_pending:
                CONNECTION_DATA_PENDING[conn] = False
                notify_all_transports()

        def update_hook(self, conn, op, db_name, table_name, rowid):
            if op in UPDATE_OPS and table_name == self.message_table_name:
                CONNECTION_DATA_PENDING[conn] = True

        def activate_sqlite_update_hook(self, sender, connection, **kwargs):
            conn = connection.connection
            if connection.vendor == 'sqlite' and hasattr(conn, "set_update_hook"):

                message_table_name = self.message_table_name
                if not message_table_name:
                    from karellen.kombu.transport.django.models import Message
                    self.message_table_name = Message._meta.db_table

                CONNECTION_DATA_PENDING[conn] = False
                conn.set_update_hook(self.update_hook)
                conn.set_commit_hook(self.commit_hook)
                conn.set_rollback_hook(self.rollback_hook)


    connection_created.connect(SqliteMessageExistsNotification().activate_sqlite_update_hook, weak=False)
