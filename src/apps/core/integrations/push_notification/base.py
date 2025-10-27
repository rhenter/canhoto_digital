import json
import logging
from typing import Dict, Optional, Any

import requests
from django.conf import settings
from requests import Timeout
from rest_framework import status

logger = logging.getLogger(__name__)

ROLES = {
    'admin', 'Administrator',
    'apartment_manager', 'ApartmentManager',
    'store', 'Store',
}


class PushNotification:
    name: str = 'OneSignal'

    def __init__(self) -> None:
        # Setting provider data
        self.app_id: str = settings.PUSH_NOTIFICATION_APP_ID
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {settings.PUSH_NOTIFICATION_API_TOKEN}"
        }
        self.url: str = settings.PUSH_NOTIFICATION_API_URL
        self.users_url: str = f"{settings.ONE_SIGNAL_API_URL}/apps/{self.app_id}/users"

    def _make_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.post(
                self.url,
                headers=self.headers,
                timeout=settings.PUSH_NOTIFICATION_API_TIMEOUT,
                data=json.dumps(data)
            )
            result = response.json()

            # Log the full response for debugging
            logger.debug(f'OneSignal API response: {result}')

            return result
        except Timeout:
            logger.error('Push Notification API Timeout')
            return {'errors': ['API Timeout']}
        except Exception as e:
            logger.error(f'Push Notification API Error: {e}')
            return {'errors': [str(e)]}

    def register_user(self, user: Any) -> Optional[Dict[str, Any]]:
        """Register a user with OneSignal using their external_id"""
        payload = {
            "identity": {
                "external_id": str(user.id)
            },
            "properties": {
                "language": getattr(user, 'language', 'en'),
                "timezone_id": getattr(user, 'timezone', 'UTC'),
            }
        }

        # Add optional user properties if available
        if hasattr(user, 'email') and user.email:
            payload["properties"]["email"] = user.email
        if hasattr(user, 'first_name') and user.first_name:
            payload["properties"]["first_name"] = user.first_name
        if hasattr(user, 'last_name') and user.last_name:
            payload["properties"]["last_name"] = user.last_name

        try:
            response = requests.post(
                self.users_url,
                headers=self.headers,
                timeout=settings.PUSH_NOTIFICATION_API_TIMEOUT,
                data=json.dumps(payload)
            )
            result = response.json()
            logger.info(f'User {user.id} registered with OneSignal: {result}')
            return result
        except Timeout:
            logger.error(f'OneSignal User Registration API Timeout for user {user.id}')
            return None
        except Exception as e:
            logger.error(f'Error registering user {user.id} with OneSignal: {e}')
            return None

    def check_user_subscriptions(self, user: Any) -> Dict[str, Any]:
        """Check if a user has active push subscriptions in OneSignal"""
        try:
            # If user doesn't have onesignal_id, they can't have subscriptions
            if not user.onesignal_id:
                logger.debug(f'User {user.id} has no onesignal_id, cannot check subscriptions')
                return {
                    'has_subscriptions': False,
                    'subscription_count': 0,
                    'error': 'User does not have OneSignal ID'
                }

            # Use the OneSignal API to get user information including subscriptions
            user_url = f"{self.users_url}/{user.onesignal_id}"
            response = requests.get(
                user_url,
                headers=self.headers,
                timeout=settings.PUSH_NOTIFICATION_API_TIMEOUT
            )

            if response.status_code == status.HTTP_200_OK:
                user_data = response.json()
                # Check if user has any push subscriptions
                subscriptions = user_data.get('subscriptions', [])
                push_subscriptions = [sub for sub in subscriptions if
                                      sub.get('type') == 'AndroidPush' or sub.get('type') == 'iOSPush']

                logger.debug(f'User {user.id} has {len(push_subscriptions)} push subscriptions')
                return {
                    'has_subscriptions': len(push_subscriptions) > 0,
                    'subscription_count': len(push_subscriptions),
                    'subscriptions': push_subscriptions
                }
            else:
                logger.warning(f'Could not fetch user {user.id} subscriptions: HTTP {response.status_code}')
                return {
                    'has_subscriptions': False,
                    'subscription_count': 0,
                    'error': f'HTTP {response.status_code}'
                }

        except Exception as e:
            logger.error(f'Error checking user {user.id} subscriptions: {e}')
            return {
                'has_subscriptions': False,
                'subscription_count': 0,
                'error': str(e)
            }

    def send_push(self, user: Any, message: str, url: str = '', title: str = '') -> Dict[str, Any]:
        from apps.user.utils import validate_register_user_with_onesignal

        # Ensure user has onesignal_id before sending push notification
        if not user.onesignal_id:
            result = self.register_user(user)
            if result and 'errors' in result:
                validated_data = validate_register_user_with_onesignal(user, result)
                if not validated_data['success']:
                    return validated_data
            # Refresh user from database to get the saved onesignal_id
            user.refresh_from_db()

        # If user still doesn't have onesignal_id, we can't send push notification
        if not user.onesignal_id:
            logger.error(f'Cannot send push notification to user {user.id}: no onesignal_id available')
            return {
                'errors': ['User does not have OneSignal ID'],
                'success': False,
                'error_type': 'no_onesignal_id',
                'error_message': 'User does not have OneSignal ID',
                'user_id': user.id
            }

        payload = {
            "app_id": self.app_id,
            "include_aliases": {
                "onesignal_id": [str(user.onesignal_id)],
            },
            "target_channel": "push",
            "contents": {"en": message, "pt": message}
        }

        # Add headings if title is provided
        if title:
            payload["headings"] = {"en": title, "pt": title}

        if url:
            payload['url'] = url
        return self._make_request(payload)

    def __repr__(self) -> str:
        return f'<{self.name}> AppID: {self.app_id}'

    def __str__(self) -> str:
        return f'AppID: {self.app_id}'
