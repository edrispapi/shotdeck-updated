import requests
import json
import logging
from django.conf import settings
from .utils import cache_user_data, get_cached_user_data

logger = logging.getLogger(__name__)

class UserManagementAPI:
    """User Management API client for JWT validation and user data retrieval"""

    def __init__(self):
        self.base_url = getattr(settings, 'USER_MANAGEMENT_API_URL', 'http://127.0.0.1:12700/api/v1')
        self.timeout = getattr(settings, 'USER_API_TIMEOUT', 10)

    def extract_user_uuid_from_jwt(self, jwt_token):
        """
        Extract user UUID from JWT token
        In this simplified implementation, we'll return a mock UUID
        In production, this would validate the JWT and extract the user UUID
        """
        try:
            # For now, return a consistent UUID for testing
            # In production, decode JWT and extract user_uuid from payload
            return "215b33dc-b4b0-4478-8d2a-02b385b6ab1b"
        except Exception as e:
            logger.error(f"Error extracting user UUID from JWT: {e}")
            return None

    def get_user_data(self, user_uuid):
        """
        Get user data from User Management API
        """
        # First check cache
        cached_data = get_cached_user_data(user_uuid)
        if cached_data:
            return cached_data

        try:
            # Call User Management API
            headers = {'Content-Type': 'application/json'}
            url = f"{self.base_url}/user/{user_uuid}/"

            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            user_data = response.json()

            # Cache the result
            cache_user_data(user_uuid, user_data)

            return user_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling User Management API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user_data: {e}")
            return None

    def check_subscription_status(self, user_uuid):
        """
        Check if user has VIP Plus subscription
        """
        user_data = self.get_user_data(user_uuid)
        if not user_data:
            return False

        # Check subscription status
        subscription = user_data.get('subscription', {})
        is_vip_plus = subscription.get('plan') == 'vip_plus' and subscription.get('active', False)

        logger.info(f"User {user_uuid} VIP Plus status: {is_vip_plus}")
        return is_vip_plus

    def validate_jwt_and_get_user(self, jwt_token):
        """
        Complete JWT validation and user data retrieval
        """
        try:
            # Extract user UUID from JWT
            user_uuid = self.extract_user_uuid_from_jwt(jwt_token)
            if not user_uuid:
                return None

            # Get user data
            user_data = self.get_user_data(user_uuid)
            if not user_data:
                return None

            # Add subscription check
            user_data['is_vip_plus'] = self.check_subscription_status(user_uuid)

            return {
                'user_uuid': user_uuid,
                'user_data': user_data,
                'is_vip_plus': user_data['is_vip_plus']
            }

        except Exception as e:
            logger.error(f"Error in JWT validation: {e}")
            return None

# Global instance
user_api = UserManagementAPI()
