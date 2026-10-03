# apps/chat/admin.py
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils import timezone

from .models import Conversation, ChatSyncLog, PendingMessageSync


# ============================================
# Small helper for rendering styled badges
# ============================================
def badge(text, color='#22c55e'):
    """Return a safe inline-styled span. Use instead of format_html when there
    are no dynamic values to interpolate."""
    return mark_safe(
        f'<span style="color:{color};font-weight:600;">{text}</span>'
    )


# ============================================
# Conversation Admin
# ============================================
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin for Conversation model - chat metadata
    """
    list_display = (
        'conversation_id_short',
        'get_patient',
        'get_doctor',
        'is_active_badge',
        'last_message_preview_short',
        'last_message_at',
        'get_unread_total',
        'get_message_count',
    )
    list_filter = (
        'is_active',
        'created_at',
        'last_message_at',
    )
    search_fields = (
        'conversation_id',
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'doctor_profile__profile__user__username',
        'doctor_profile__profile__user__email',
        'last_message_preview',
    )
    raw_id_fields = (
        'patient_profile',
        'doctor_profile',
        'consultation',
        'last_message_sender',
    )
    readonly_fields = (
        'conversation_id',
        'started_at',
        'created_at',
        'updated_at',
        'get_message_count_display',
    )
    date_hierarchy = 'created_at'
    ordering = ('-last_message_at', '-created_at')

    fieldsets = (
        ('Conversation Info', {
            'fields': ('conversation_id', 'consultation', 'is_active')
        }),
        ('Participants', {
            'fields': ('patient_profile', 'doctor_profile')
        }),
        ('Last Message', {
            'fields': ('last_message_preview', 'last_message_at', 'last_message_sender')
        }),
        ('Unread Counts', {
            'fields': ('unread_count_patient', 'unread_count_doctor')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'ended_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('get_message_count_display',),
            'classes': ('collapse',)
        }),
    )

    # ── Columns ────────────────────────────────────
    @admin.display(description='ID', ordering='conversation_id')
    def conversation_id_short(self, obj):
        return obj.conversation_id[:8] + '...' if obj.conversation_id else '-'

    @admin.display(description='Patient',
                   ordering='patient_profile__profile__user__first_name')
    def get_patient(self, obj):
        if obj.patient_profile and obj.patient_profile.profile:
            return obj.patient_profile.profile.user.get_full_name()
        return '-'

    @admin.display(description='Doctor',
                   ordering='doctor_profile__profile__user__first_name')
    def get_doctor(self, obj):
        if obj.doctor_profile and obj.doctor_profile.profile:
            return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
        return '-'

    @admin.display(description='Status')
    def is_active_badge(self, obj):
        if obj.is_active:
            return badge('🟢 Active', '#22c55e')
        return badge('🔴 Inactive', '#94a3b8')

    @admin.display(description='Last Message')
    def last_message_preview_short(self, obj):
        if obj.last_message_preview:
            return (obj.last_message_preview[:50]
                    + ('...' if len(obj.last_message_preview) > 50 else ''))
        return '-'

    @admin.display(description='Unread')
    def get_unread_total(self, obj):
        total = (obj.unread_count_patient or 0) + (obj.unread_count_doctor or 0)
        if total > 0:
            return format_html(
                '<span style="color:#ef4444;font-weight:bold;">{}</span>',
                total,
            )
        return format_html('<span style="color:#22c55e;">{}</span>', '0')

    @admin.display(description='Messages')
    def get_message_count(self, obj):
        # Message count is stored in Flask; placeholder here.
        return 'N/A'

    @admin.display(description='Message Count')
    def get_message_count_display(self, obj):
        return 'Message count available via Flask API'

    # ── Actions ────────────────────────────────────
    actions = ['end_conversations', 'mark_as_active', 'reset_unread_counts']

    @admin.action(description='End selected conversations')
    def end_conversations(self, request, queryset):
        updated = 0
        for conv in queryset:
            if conv.is_active:
                conv.is_active = False
                conv.ended_at = timezone.now()
                conv.save(update_fields=['is_active', 'ended_at'])
                updated += 1
        self.message_user(request, f'{updated} conversations ended.')

    @admin.action(description='Mark as Active')
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True, ended_at=None)
        self.message_user(request, f'{updated} conversations marked as active.')

    @admin.action(description='Reset Unread Counts')
    def reset_unread_counts(self, request, queryset):
        updated = queryset.update(
            unread_count_patient=0,
            unread_count_doctor=0,
        )
        self.message_user(request, f'{updated} conversations unread counts reset.')


# ============================================
# ChatSyncLog Admin
# ============================================
@admin.register(ChatSyncLog)
class ChatSyncLogAdmin(admin.ModelAdmin):
    """
    Admin for ChatSyncLog - track sync status with Flask
    """
    list_display = (
        'id',
        'conversation',
        'sync_type_display',
        'flask_conversation_id',
        'is_successful_badge',
        'synced_at',
    )
    list_filter = ('sync_type', 'is_successful', 'synced_at')
    search_fields = (
        'conversation__conversation_id',
        'flask_conversation_id',
        'error_message',
    )
    raw_id_fields = ('conversation',)
    readonly_fields = ('synced_at', 'created_at', 'updated_at')
    date_hierarchy = 'synced_at'
    ordering = ('-synced_at',)

    fieldsets = (
        ('Sync Info', {
            'fields': ('conversation', 'sync_type', 'flask_conversation_id')
        }),
        ('Details', {
            'fields': ('details', 'is_successful', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('synced_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Type')
    def sync_type_display(self, obj):
        return obj.get_sync_type_display()

    @admin.display(description='Status')
    def is_successful_badge(self, obj):
        if obj.is_successful:
            return badge('✅ Success', '#22c55e')
        return badge('❌ Failed', '#ef4444')

    @admin.display(description='Error')
    def error_message_short(self, obj):
        if not obj.error_message:
            return '-'
        return (obj.error_message[:50]
                + ('...' if len(obj.error_message) > 50 else ''))

    actions = ['retry_failed_syncs']

    @admin.action(description='Retry failed syncs')
    def retry_failed_syncs(self, request, queryset):
        updated = queryset.filter(is_successful=False).update(is_successful=True)
        self.message_user(request, f'{updated} syncs marked for retry.')


# ============================================
# PendingMessageSync Admin
# ============================================
@admin.register(PendingMessageSync)
class PendingMessageSyncAdmin(admin.ModelAdmin):
    """
    Admin for PendingMessageSync - queue for messages to sync
    """
    list_display = (
        'id',
        'conversation',
        'attempt_count_display',
        'max_attempts',
        'last_attempt',
        'is_processed_badge',
    )
    list_filter = ('is_processed', 'attempt_count', 'created_at')
    search_fields = (
        'conversation__conversation_id',
        'message_data',
    )
    raw_id_fields = ('conversation',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Message Sync', {
            'fields': ('conversation', 'message_data', 'is_processed')
        }),
        ('Attempts', {
            'fields': ('attempt_count', 'max_attempts', 'last_attempt')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Attempts')
    def attempt_count_display(self, obj):
        return f"{obj.attempt_count}/{obj.max_attempts}"

    @admin.display(description='Status')
    def is_processed_badge(self, obj):
        if obj.is_processed:
            return badge('✅ Processed', '#22c55e')
        return badge('⏳ Pending', '#f59e0b')

    actions = ['process_pending_syncs', 'reset_attempts']

    @admin.action(description='Mark as Processed')
    def process_pending_syncs(self, request, queryset):
        updated = queryset.filter(is_processed=False).update(
            is_processed=True,
            attempt_count=1,
        )
        self.message_user(request, f'{updated} pending syncs marked as processed.')

    @admin.action(description='Reset attempts for retry')
    def reset_attempts(self, request, queryset):
        updated = queryset.update(
            attempt_count=0,
            last_attempt=None,
            is_processed=False,
        )
        self.message_user(request, f'{updated} syncs reset for retry.')