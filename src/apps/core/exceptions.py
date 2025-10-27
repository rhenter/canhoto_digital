class BadGatewayResponseApiError(Exception):
    pass


class APINotAvailableOrOffline(Exception):
    def __init__(self, msg='', *args, **kwargs):
        if not msg:
            msg = 'API server is offline or unreachable.'

        url = kwargs.pop('url', '')
        if url:
            msg += f' URL: {url}.'

        response = kwargs.pop('response', None)
        if response:
            msg += f' Response. ({response.status_code}) {response.text}.'
        super().__init__(msg, *args, **kwargs)


class SqsQueueDoesNotExist(Exception):
    pass


class SnsTopicDoesNotExist(Exception):
    pass
