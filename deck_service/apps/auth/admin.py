from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.auth.models import User, OTPCODE, VIPToken


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('uuid', 'username', 'phone_number', 'email', 'is_verified', 'is_vip', 'date_joined')
    list_filter = ('is_verified', 'is_vip', 'date_joined')
    search_fields = ('uuid', 'username', 'phone_number', 'email')
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('uuid', 'phone_number', 'age', 'ip_address', 'is_verified', 'is_vip', 'vip_expires_at')
        }),
    )
    readonly_fields = ('uuid',)


@admin.register(OTPCODE)
class OTPCODEAdmin(admin.ModelAdmin):
    list_display = ('temp_user_id', 'code', 'user', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('temp_user_id', 'code', 'user__phone_number')
    readonly_fields = ('created_at',)


@admin.register(VIPToken)
class VIPTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_active', 'expires_at', 'created_at')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__phone_number', 'token')
    readonly_fields = ('token', 'created_at')
