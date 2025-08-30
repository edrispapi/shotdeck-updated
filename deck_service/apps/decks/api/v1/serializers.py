from rest_framework import serializers
from apps.decks.models import Deck

class DeckSerializer(serializers.ModelSerializer):
    # نام کاربری مالک را به صورت فقط خواندنی نمایش می‌دهیم
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Deck
        fields = [
            'id', 
            'title', 
            'description', 
            'owner', 
            'owner_username', 
            'image_ids', 
            'created_at', 
            'updated_at'
        ]
        # فیلد owner در زمان ایجاد به صورت خودکار از کاربر لاگین کرده پر می‌شود
        read_only_fields = ('owner', 'owner_username', 'created_at', 'updated_at')