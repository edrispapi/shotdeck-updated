from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
from apps.auth.models import User, OTPCODE, VIPToken
from .serializers import (
    SignupStep1Serializer, SignupStep2Serializer,
    UserProfileSerializer, LoginSerializer, VIPTokenSerializer
)
from messaging.producers import send_event


class AuthView(APIView):
    """Simple authentication that returns user_uuid"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Get user_uuid from JWT and return it
        Without complex authentication operations
        """
        # Here JWT is decoded and user_uuid is extracted
        # For now, return a sample user_uuid
        user_uuid = "215b33dc-b4b0-4478-8d2a-02b385b6ab1b"

        # Send event to Kafka to check subscription
        send_event('user_access_check', {
            'user_uuid': user_uuid,
            'timestamp': timezone.now().isoformat(),
            'page': 'shotdeck_main'
        })

        return Response({
            'user_uuid': user_uuid,
            'status': 'access_granted',
            'message': 'User can access the page'
        }, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    """Get user profile"""

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class VIPSubscriptionView(APIView):
    """Handle VIP subscription"""

    def post(self, request):
        user = request.user

        # Create VIP token
        vip_token, created = VIPToken.objects.get_or_create(
            user=user,
            defaults={'expires_at': timezone.now() + timedelta(days=30)}
        )

        if created:
            # Update user VIP status
            user.is_vip = True
            user.vip_expires_at = vip_token.expires_at
            user.save()

            # Send VIP membership event to Kafka
            send_event('user_vip_activated', {
                'user_id': str(user.uuid),
                'vip_token': str(vip_token.token),
                'expires_at': vip_token.expires_at.isoformat()
            })

        serializer = VIPTokenSerializer(vip_token)
        return Response({
            'vip_token': serializer.data,
            'message': 'VIP subscription activated'
        }, status=status.HTTP_200_OK)


class VIPStatusView(APIView):
    """Check VIP status"""

    def get(self, request):
        user = request.user

        try:
            vip_token = user.vip_token
            if vip_token.is_active and (vip_token.expires_at is None or vip_token.expires_at > timezone.now()):
                serializer = VIPTokenSerializer(vip_token)
                return Response({
                    'is_vip': True,
                    'vip_token': serializer.data
                })
            else:
                return Response({'is_vip': False, 'message': 'VIP expired'})
        except VIPToken.DoesNotExist:
            return Response({'is_vip': False, 'message': 'Not a VIP member'})
