# apps/auth/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.auth.models import User
from messaging.producers import send_event


@receiver(post_save, sender=User)
def send_user_created_event(sender, instance, created, **kwargs):
    """Send user_created event to Kafka when a new user is created"""
    if created:
        send_event('user_created', {
            'user_id': str(instance.uuid),
            'phone_number': instance.phone_number,
            'created_at': instance.date_joined.isoformat()
        })
