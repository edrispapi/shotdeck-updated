from django.contrib import admin
from .models import Deck

@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at')
    list_filter = ('owner',)
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    # --- تغییر کلیدی: اضافه کردن فایل‌های استاتیک سفارشی به این مدل در ادمین ---
    class Media:
        css = {
            'all': ('decks/css/admin_custom.css',)
        }