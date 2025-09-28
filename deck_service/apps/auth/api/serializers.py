from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from apps.auth.models import User, OTPCODE, VIPToken


class SignupStep1Serializer(serializers.Serializer):
    """Serializer for signup step 1 - Send OTP"""
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already exists")
        return value


class SignupStep2Serializer(serializers.Serializer):
    """Serializer for signup step 2 - Verify OTP"""
    temp_user_id = serializers.CharField(max_length=100)
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        temp_user_id = attrs.get('temp_user_id')
        otp_code = attrs.get('otp_code')

        try:
            otp_obj = OTPCODE.objects.get(
                temp_user_id=temp_user_id,
                code=otp_code,
                is_used=False
            )

            if otp_obj.is_expired():
                raise serializers.ValidationError("OTP has expired")

            attrs['otp_obj'] = otp_obj
            return attrs
        except OTPCODE.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP or temp_user_id")


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    class Meta:
        model = User
        fields = ['uuid', 'username', 'email', 'phone_number', 'age', 'ip_address', 'is_verified', 'is_vip']
        read_only_fields = ['uuid', 'is_verified', 'is_vip']


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        if phone_number and password:
            user = authenticate(phone_number=phone_number, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials")
            if not user.is_verified:
                raise serializers.ValidationError("Account not verified")
        else:
            raise serializers.ValidationError("Phone number and password are required")

        attrs['user'] = user
        return attrs


class VIPTokenSerializer(serializers.ModelSerializer):
    """Serializer for VIP tokens"""
    class Meta:
        model = VIPToken
        fields = ['token', 'created_at', 'expires_at', 'is_active']
        read_only_fields = ['token', 'created_at']
