import importlib
import logging

import requests
from django.conf import settings
from requests import Timeout

logger = logging.getLogger(__name__)


class WhatsAppBase:
    name = ''
    url_base = ''

    def __init__(self, instance_id, access_token, timeout=3, **kwargs):
        # Setting provider data
        self.instance_id = instance_id
        self.access_token = access_token
        self.timeout = timeout
        self.url = self._get_full_url()

    def _get_full_url(self):
        return self.url_base

    def _make_request(self, data):
        try:
            response = requests.post(self.url, data=data)
            return response
        except Timeout:
            logger.error(f'WhatsApp: {self.name} API Timeout.')

    def send_message(self, cellphone, text_message, uid=0):
        return 'Not Implemented.'

    def __repr__(self):
        return f'<WhatsApp: {self.name}> InstanceID: {self.instance_id}'

    def __str__(self):
        return f'App{self.name}'


def get_default_provider():
    whatsapp_attributes = settings.WHATSAPP_PROVIDERS.get(settings.DEFAULT_WHATSAPP_PROVIDER)
    whatsapp_module = importlib.import_module('apps.core.integrations.whatsapp')
    WhatsAppProvider = getattr(whatsapp_module, whatsapp_attributes.get('class'))
    return WhatsAppProvider(**whatsapp_attributes)
