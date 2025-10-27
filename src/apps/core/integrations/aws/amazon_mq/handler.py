import logging
import ssl
from typing import Any, Dict, List, Optional, Union

import pika
from django.conf import settings
from pika.exceptions import StreamLostError, ChannelWrongStateError, ConnectionWrongStateError

logging.getLogger("pika").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def run_cmd(obj: Any, attr: str, is_method: bool = True, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> Any:
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    if '.' in attr:
        attrs = attr.split('.')
        method = obj
        for _attr in attrs:
            method = getattr(method, _attr)
    else:
        method = getattr(obj, attr)
    if args and is_method:
        return method(*args, **kwargs)
    return method


class AmazonMqHandler:
    def __init__(self, connection_url: str = '') -> None:
        if not connection_url:
            connection_url = settings.CELERY_BROKER_URL
        self.connection_url = connection_url
        self.connection = self._start_connection()
        self._channel = self._create_channel()

    @property
    def channel(self) -> pika.channel.Channel:
        try:
            channel = self._channel
        except (StreamLostError, ChannelWrongStateError):
            channel = self._create_channel()
        return channel

    def _create_channel(self) -> pika.channel.Channel:
        try:
            channel = self.connection.channel()
        except ConnectionWrongStateError:
            connection = self._start_connection()
            channel = connection.channel()
        return channel

    def _run_channel_method(self, method: str, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        try:
            channel = self.channel
            response = run_cmd(obj=channel, attr=method, is_method=True, args=args, kwargs=kwargs)
        except (StreamLostError, ChannelWrongStateError):
            channel = self._create_channel()
            response = run_cmd(obj=channel, attr=method, is_method=True, args=args, kwargs=kwargs)
        return response

    def _start_connection(self) -> pika.BlockingConnection:
        parameters = pika.URLParameters(self.connection_url)
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.set_ciphers('ECDHE+AESGCM:!ECDSA')
        parameters.ssl_options = pika.SSLOptions(context=ssl_context)
        connection = pika.BlockingConnection(parameters)
        return connection

    def delete_queue(self, queue_name: str) -> Any:
        return self._run_channel_method(
            method='queue_delete',
            args=[queue_name]
        )

    def _get_queue(self, channel: pika.channel.Channel, queue_name: str) -> Any:
        return channel.queue_declare(
            queue=queue_name, durable=True,
            exclusive=False, auto_delete=False
        )

    def get_queue(self, queue_name: str) -> Any:
        try:
            queue = self._get_queue(self.channel, queue_name)
        except (StreamLostError, ChannelWrongStateError):
            channel = self._create_channel()
            queue = self._get_queue(channel, queue_name)
        return queue

    def get_queue_detail(self, queue_name: str) -> Dict[str, Any]:
        queue = self.get_queue(queue_name)
        return queue.method.__dict__

    def get_message_count(self, queue_name: str) -> int:
        queue = self.get_queue(queue_name)
        return queue.method.message_count

    def purge_messages(self, queue_name: str) -> Any:
        return self._run_channel_method(
            method='queue_purge',
            args=[queue_name],
        )

    def get_queue_details(self, queues: List[str] = None) -> List[Dict[str, Any]]:
        if not queues:
            queues = [queue.name for queue in settings.CELERY_QUEUES]

        details = []
        logger.debug(f'Details from: {settings.ENVIRONMENT_NAME} environment')
        for queue_name in queues:
            details.append(self.get_queue_detail(queue_name))

        return details
