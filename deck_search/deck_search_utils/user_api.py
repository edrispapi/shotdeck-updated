# Minimal user API for deck_search service
# This is a placeholder since deck_search doesn't need full user management

class UserAPI:
    def get_user_info(self, user_id):
        # Placeholder - return minimal user info
        return {
            'id': user_id,
            'username': f'user_{user_id}',
            'email': f'user_{user_id}@example.com'
        }

    def validate_token(self, token):
        # Placeholder - always return valid for now
        return {'user_id': 1, 'valid': True}

# Singleton instance
user_api = UserAPI()
