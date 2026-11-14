from rest_framework import serializers


class RegisterDeviceSerializer(serializers.Serializer):
    token = serializers.CharField(
        max_length=4096,
        trim_whitespace=True,
    )

    def validate_token(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "A registration token is required."
            )

        return value
    
# notifications/serializers.py
from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """
    Read serializer for the notification list / detail views.

    The frontend gets everything it needs to render a list item:
      title, message, priority, icon type, unread flag, click target.
    """
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True,
    )
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True,
    )
    age_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_id',
            'notification_type',
            'notification_type_display',
            'priority',
            'priority_display',
            'title',
            'message',
            'body',
            'is_read',
            'read_at',
            'is_dismissed',
            'dismissed_at',
            'is_expired',
            'related_url',
            'related_object_id',
            'related_object_type',
            'data',
            'created_at',
            'age_seconds',
        ]
        read_only_fields = fields   # the list endpoint is read-only

    def get_age_seconds(self, obj):
        from django.utils import timezone
        if not obj.created_at:
            return None
        return int((timezone.now() - obj.created_at).total_seconds())


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Full read/write serializer so the frontend can toggle channels/categories.
    """
    class Meta:
        model = NotificationPreference
        fields = [
            'appointment_notifications',
            'consultation_notifications',
            'chat_notifications',
            'prescription_notifications',
            'lab_notifications',
            'payment_notifications',
            'queue_notifications',
            'referral_notifications',
            'system_notifications',
            'email_enabled',
            'sms_enabled',
            'push_enabled',
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
        ]    