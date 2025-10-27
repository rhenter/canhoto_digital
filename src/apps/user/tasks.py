import time

from celery.utils.log import get_task_logger
from django.apps import apps as django_apps

from proj_settings.celery import celery_app as app
from proj_settings.utils import calculate_duration
from .utils import register_user_with_onesignal

logger = get_task_logger(__name__)


@app.task(name='register_user_with_onesignal')
def register_user_with_onesignal_task(user_id):
    """Register a user with OneSignal for push notifications"""
    start_time = time.perf_counter()

    user_model = django_apps.get_model('user', 'User')
    try:
        user = user_model.objects.get(id=user_id)
    except user_model.DoesNotExist:
        logger.error(f"User with ID {user_id} not found for OneSignal registration")
        return {
            'error': f'User with ID {user_id} not found',
            'duration': '0s',
        }

    logger.debug(f"register_user_with_onesignal: User: {user}")

    # Register user with OneSignal using shared utility
    result = register_user_with_onesignal(user)

    end_time = time.perf_counter()
    duration = calculate_duration(start_time, end_time)
    logger.debug(f'register_user_with_onesignal ended. Duration: {duration}')

    return {
        'user': str(user),
        'user_id': user_id,
        'onesignal_result': result['result'],
        'success': result['success'],
        'error_type': result['error_type'],
        'error_message': result['error_message'],
        'duration': duration,
        'status': 'success' if result['success'] else 'failed'
    }
