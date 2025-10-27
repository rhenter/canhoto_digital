import logging
from rest_framework import status

from .base import WhatsAppBase

logger = logging.getLogger(__name__)


class WaboxAppProvider(WhatsAppBase):
    name = 'WaboxApp'
    url_base = 'https://www.waboxapp.com/api/send/chat'

    def _get_full_url(self):
        return self.url_base

    def send_message(self, cellphone, text_message, uid=''):
        custom_uid = f'msg-{str(uid).zfill(4)}'
        data = {
            'token': self.access_token,
            'uid': self.instance_id,
            'to': cellphone,
            'custom_uid': custom_uid,
            'text': text_message
        }
        response = self._make_request(data=data)
        if response.status_code != status.HTTP_200_OK:
            error = response.json().get('error')
            if 'custom_uid' in error:
                uid += uid
                return self.send_message(cellphone, text_message, uid)
            return False
        return True
