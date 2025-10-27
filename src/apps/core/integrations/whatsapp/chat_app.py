import logging
from rest_framework import status

from apps.core.integrations.whatsapp.base import WhatsAppBase

logger = logging.getLogger(__name__)


class ChatAPIProvider(WhatsAppBase):
    name = 'ChatAPI'
    url_base = 'https://eu113.chat-api.com/instance{instance_id}/sendMessage?token={token}'

    def _get_full_url(self):
        return self.url_base.format(
            instance_id=self.instance_id,
            token=self.access_token
        )

    def send_message(self, cellphone, text_message, uid=''):
        data = {
            'phone': cellphone,
            'body': text_message
        }
        response = self._make_request(data=data)
        if response.status_code != status.HTTP_200_OK:
            logger.error(f'{self.name} Zicado: {response.text}')
            return False
        return True
