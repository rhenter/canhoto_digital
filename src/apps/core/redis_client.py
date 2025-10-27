import redis

from django.conf import settings


def get_redis_client():
    cache_url = settings.CACHES['default']['LOCATION']
    return redis.from_url(
        cache_url,
        decode_responses=True
    )
