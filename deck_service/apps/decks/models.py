from django.db import models
from django.contrib.auth.models import User

class Deck(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    
    # --- تغییر کلیدی: ذخیره کردن slug به جای id ---
    image_slugs = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"'{self.title}' by {self.owner.username}"