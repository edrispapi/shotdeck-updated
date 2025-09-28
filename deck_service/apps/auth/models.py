from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
import random
import string


class User(AbstractUser):
    """Custom User model with additional fields"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_vip = models.BooleanField(default=False)
    vip_expires_at = models.DateTimeField(null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_permissions'
    )

    def __str__(self):
        return self.username or self.phone_number or str(self.uuid)


class OTPCODE(models.Model):
    """OTP codes for user verification"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    temp_user_id = models.CharField(max_length=100, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generate_otp(cls):
        """Generate 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))

    @classmethod
    def generate_temp_user_id(cls):
        """Generate temporary user ID"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=50))

    def is_expired(self):
        return timezone.now() > self.expires_at


class VIPToken(models.Model):
    """VIP membership tokens"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vip_token')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"VIP Token for {self.user.username}"
