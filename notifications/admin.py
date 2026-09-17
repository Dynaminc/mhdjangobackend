# apps/notifications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Notification, NotificationPreference


# ============================================
# Notification Admin
# ============================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'notification_id',
        'user',
        'notification_type',
        'title_short',
        'priority_badge',
        'is_read_badge',
        'is_delivered_badge',
        'created_at'
    )
    list_filter = (
        'notification_type',
        'priority',
        'is_read',
        'is_delivered',
        'is_dismissed',
        'is_expired',
        'created_at'
    )
    search_fields = (
        'notification_id',
        'user__username',
        'user__email',
        'title',
        'message'
    )
    raw_id_fields = ('user', 'patient_profile', 'doctor_profile')
    readonly_fields = ('notification_id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('notification_id', 'user', 'notification_type', 'priority')
        }),
        ('Content', {
            'fields': ('title', 'message', 'body')
        }),
        ('Related Object', {
            'fields': ('related_object_id', 'related_object_type', 'related_url', 'data')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_delivered', 'delivered_at', 'delivered_via')
        }),
        ('Action', {
            'fields': ('action_taken', 'action_taken_at', 'action_type', 'is_dismissed', 'dismissed_at')
        }),
        ('Expiry', {
            'fields': ('expires_at', 'is_expired')
        }),
        ('Target Profiles', {
            'fields': ('patient_profile', 'doctor_profile'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def title_short(self, obj):
        return obj.title[:40] + ('...' if len(obj.title) > 40 else '')
    title_short.short_description = 'Title'
    
    def priority_badge(self, obj):
        colors = {
            'low': '#94a3b8',
            'medium': '#3b82f6',
            'high': '#f59e0b',
            'urgent': '#ef4444',
            'critical': '#dc2626'
        }
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            colors.get(obj.priority, '#94a3b8'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: #22c55e;">✅ Read</span>')
        return format_html('<span style="color: #ef4444;">🔴 Unread</span>')
    is_read_badge.short_description = 'Status'
    
    def is_delivered_badge(self, obj):
        if obj.is_delivered:
            return format_html('<span style="color: #22c55e;">✅ Delivered</span>')
        return format_html('<span style="color: #f59e0b;">⏳ Pending</span>')
    is_delivered_badge.short_description = 'Delivery'
    
    actions = [
        'mark_as_read', 'mark_as_unread', 'mark_as_delivered',
        'dismiss_notifications', 'expire_notifications'
    ]
    
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                updated += 1
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark as Read'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark as Unread'
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_delivered=True, delivered_at=timezone.now())
        self.message_user(request, f'{updated} notifications marked as delivered.')
    mark_as_delivered.short_description = 'Mark as Delivered'
    
    def dismiss_notifications(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for notification in queryset:
            if not notification.is_dismissed:
                notification.dismiss()
                updated += 1
        self.message_user(request, f'{updated} notifications dismissed.')
    dismiss_notifications.short_description = 'Dismiss Notifications'
    
    def expire_notifications(self, request, queryset):
        updated = 0
        for notification in queryset:
            if not notification.is_expired:
                notification.expire()
                updated += 1
        self.message_user(request, f'{updated} notifications expired.')
    expire_notifications.short_description = 'Expire Notifications'


# ============================================
# NotificationPreference Admin
# ============================================
@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'appointment_notifications',
        'consultation_notifications',
        'chat_notifications',
        'prescription_notifications',
        'lab_notifications',
        'quiet_hours_enabled'
    )
    list_filter = (
        'appointment_notifications',
        'consultation_notifications',
        'chat_notifications',
        'prescription_notifications',
        'lab_notifications',
        'payment_notifications',
        'queue_notifications',
        'system_notifications',
        'email_enabled',
        'sms_enabled',
        'push_enabled',
        'quiet_hours_enabled'
    )
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Notification Categories', {
            'fields': (
                'appointment_notifications',
                'consultation_notifications',
                'chat_notifications',
                'prescription_notifications',
                'lab_notifications',
                'payment_notifications',
                'queue_notifications',
                'system_notifications'
            )
        }),
        ('Channels', {
            'fields': ('email_enabled', 'sms_enabled', 'push_enabled')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )