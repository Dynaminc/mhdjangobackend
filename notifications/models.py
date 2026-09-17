from django.db import models

# Create your models here.
# apps/notifications/models.py
from django.db import models
from django.contrib.auth.models import User
from accounts.models import BaseModel, Profile, DoctorProfile, PatientProfile
from django.utils import timezone
import uuid
from django.db.models import Q


# ============================================
# NOTIFICATION MODEL
# ============================================
class Notification(BaseModel):
    """
    Central notification model for all system notifications.
    Supports multiple types, priorities, and delivery channels.
    """
    
    NOTIFICATION_TYPES = (
        # Appointment notifications
        ('appointment_created', 'Appointment Created'),
        ('appointment_confirmed', 'Appointment Confirmed'),
        ('appointment_cancelled', 'Appointment Cancelled'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('appointment_completed', 'Appointment Completed'),
        ('appointment_no_show', 'No-Show Notification'),
        
        # Consultation notifications
        ('consultation_started', 'Consultation Started'),
        ('consultation_completed', 'Consultation Completed'),
        ('consultation_scheduled', 'Consultation Scheduled'),
        ('consultation_reminder', 'Consultation Reminder'),
        ('consultation_notes_added', 'Consultation Notes Added'),
        
        # Chat notifications
        ('chat_message', 'New Message'),
        ('chat_read', 'Message Read'),
        ('chat_typing', 'Typing Indicator'),
        
        # Prescription notifications
        ('prescription_created', 'Prescription Created'),
        ('prescription_refilled', 'Prescription Refilled'),
        ('prescription_expiring', 'Prescription Expiring Soon'),
        ('prescription_ready', 'Prescription Ready for Pickup'),
        ('refill_requested', 'Refill Requested'),
        ('refill_approved', 'Refill Approved'),
        ('refill_rejected', 'Refill Rejected'),
        
        # Lab notifications
        ('lab_ordered', 'Lab Test Ordered'),
        ('lab_results_ready', 'Lab Results Ready'),
        ('lab_abnormal', 'Abnormal Lab Result'),
        ('lab_critical', 'Critical Lab Result'),
        
        # Payment notifications
        ('payment_success', 'Payment Successful'),
        ('payment_failed', 'Payment Failed'),
        ('payment_refunded', 'Payment Refunded'),
        ('invoice_ready', 'Invoice Ready'),
        
        # Queue notifications
        ('queue_position_updated', 'Queue Position Updated'),
        ('queue_admitted', 'Admitted from Queue'),
        ('queue_waiting', 'Waiting in Queue'),
        
        # Medical record notifications
        ('record_updated', 'Medical Record Updated'),
        ('allergy_added', 'Allergy Added'),
        ('medication_added', 'Medication Added'),
        
        # System notifications
        ('system_alert', 'System Alert'),
        ('maintenance', 'Maintenance Notice'),
        ('security_alert', 'Security Alert'),
        ('account_updated', 'Account Updated'),
        ('profile_updated', 'Profile Updated'),
        
        # General
        ('info', 'Information'),
        ('reminder', 'Reminder'),
        ('alert', 'Alert'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    )
    
    DELIVERY_CHANNEL_CHOICES = (
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('all', 'All Channels'),
    )
    
    # ============================================
    # Core Fields
    # ============================================
    
    # Unique identifier for the notification
    notification_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique notification ID (e.g., NOT-2026-001)",
        blank=True,          # allow blank during form validation
        editable=False,      # hide from admin — we set it ourselves
        default=uuid.uuid4,
    )
    
    # Target user (who receives the notification)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user receiving this notification"
    )
    
    # Optional: target profile (patient or doctor)
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Target patient profile (if applicable)"
    )
    doctor_profile = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Target doctor profile (if applicable)"
    )
    
    # ============================================
    # Notification Content
    # ============================================
    
    # Type and priority
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        db_index=True,
        help_text="Type of notification"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Priority level"
    )
    
    # Content
    title = models.CharField(
        max_length=255,
        help_text="Short title for the notification"
    )
    message = models.TextField(
        help_text="Main message content"
    )
    body = models.TextField(
        blank=True,
        help_text="Extended message body (for email/push)"
    )
    
    # ============================================
    # Metadata
    # ============================================
    
    # Related object references
    related_object_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="ID of related object (e.g., appointment_id)"
    )
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of related object (e.g., 'appointment', 'consultation')"
    )
    related_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL to navigate to when notification is clicked"
    )
    
    # Additional data (JSON)
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data for the notification"
    )
    
    # ============================================
    # Delivery and Status
    # ============================================
    
    # Read status
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the notification has been read"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was read"
    )
    
    # Delivery status
    delivered_via = models.CharField(
        max_length=50,
        choices=DELIVERY_CHANNEL_CHOICES,
        default='in_app',
        help_text="How the notification was delivered"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was delivered"
    )
    is_delivered = models.BooleanField(
        default=False,
        help_text="Whether the notification was successfully delivered"
    )
    
    # Action status
    action_taken = models.BooleanField(
        default=False,
        help_text="Whether the user has taken action on this notification"
    )
    action_taken_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When action was taken"
    )
    action_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of action taken (e.g., 'viewed', 'accepted', 'dismissed')"
    )
    
    # Dismiss status
    is_dismissed = models.BooleanField(
        default=False,
        help_text="Whether the notification was dismissed by the user"
    )
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was dismissed"
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this notification expires"
    )
    is_expired = models.BooleanField(
        default=False,
        help_text="Whether this notification has expired"
    )
    
    # ============================================
    # Methods
    # ============================================
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Auto-generate notification ID if not set
        if not self.notification_id:
            year = timezone.now().year
            count = Notification.objects.filter(
                created_at__year=year
            ).count() + 1
            self.notification_id = f"NOT-{year}-{str(count).zfill(4)}"
        
        # Auto-expire if past expiry date
        if self.expires_at and self.expires_at <= timezone.now():
            self.is_expired = True
        
        super().save(*args, **kwargs)
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        if not self.is_delivered:
            self.is_delivered = True
            self.delivered_at = timezone.now()
            self.save(update_fields=['is_delivered', 'delivered_at'])
    
    def dismiss(self):
        """Dismiss the notification"""
        if not self.is_dismissed:
            self.is_dismissed = True
            self.dismissed_at = timezone.now()
            self.save(update_fields=['is_dismissed', 'dismissed_at'])
    
    def take_action(self, action_type='viewed'):
        """Mark that the user took action on this notification"""
        if not self.action_taken:
            self.action_taken = True
            self.action_taken_at = timezone.now()
            self.action_type = action_type
            self.save(update_fields=['action_taken', 'action_taken_at', 'action_type'])
    
    def expire(self):
        """Expire the notification"""
        if not self.is_expired:
            self.is_expired = True
            self.save(update_fields=['is_expired'])
    
    @classmethod
    def get_unread_count(cls, user):
        """Get unread notification count for a user"""
        return cls.objects.filter(
            user=user,
            is_read=False,
            is_expired=False,
            is_dismissed=False
        ).count()
    
    @classmethod
    def get_user_notifications(cls, user, limit=50, include_read=False):
        """Get notifications for a user"""
        queryset = cls.objects.filter(
            user=user,
            is_expired=False,
            is_dismissed=False
        )
        
        if not include_read:
            queryset = queryset.filter(is_read=False)
        
        return queryset.order_by('-created_at')[:limit]
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification_id']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['is_expired', 'is_dismissed']),
        ]


# ============================================
# NOTIFICATION PREFERENCE
# ============================================
class NotificationPreference(BaseModel):
    """
    User preferences for notification types and channels.
    """
    
    # Target user
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text="The user these preferences belong to"
    )
    
    # Preferences by category
    appointment_notifications = models.BooleanField(default=True)
    consultation_notifications = models.BooleanField(default=True)
    chat_notifications = models.BooleanField(default=True)
    prescription_notifications = models.BooleanField(default=True)
    lab_notifications = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    queue_notifications = models.BooleanField(default=True)
    system_notifications = models.BooleanField(default=True)
    
    # Channel preferences
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start of quiet hours (e.g., 22:00)"
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End of quiet hours (e.g., 07:00)"
    )
    quiet_hours_enabled = models.BooleanField(
        default=False,
        help_text="Whether quiet hours are enabled"
    )
    
    def __str__(self):
        return f"{self.user.get_full_name()}'s Preferences"
    
    @classmethod
    def get_preferences(cls, user):
        """Get or create preferences for a user"""
        prefs, created = cls.objects.get_or_create(user=user)
        return prefs


# ============================================
# NOTIFICATION CENTRAL SIGNAL HANDLER
# ============================================
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import connection


class NotificationSignalHandler:
    """
    Central handler for all notification triggers.
    This class checks if notifications need to be created and creates them.
    """
    
    @staticmethod
    def create_notification(user, notification_type, title, message, **kwargs):
        """
        Central method to create a notification.
        """
        # Check if user has notifications enabled
        try:
            prefs = NotificationPreference.objects.get(user=user)
        except NotificationPreference.DoesNotExist:
            # Default: create with all enabled
            prefs = NotificationPreference.objects.create(user=user)
        
        # Check if this notification type is enabled
        type_map = {
            'appointment': prefs.appointment_notifications,
            'consultation': prefs.consultation_notifications,
            'chat': prefs.chat_notifications,
            'prescription': prefs.prescription_notifications,
            'lab': prefs.lab_notifications,
            'payment': prefs.payment_notifications,
            'queue': prefs.queue_notifications,
            'system': prefs.system_notifications,
        }
        
        # Determine category from notification_type
        category = None
        for key in type_map:
            if notification_type.startswith(key):
                category = key
                break
        
        # If category not found, check if it's a system notification
        if not category:
            category = 'system'
        
        # If notifications are disabled for this category, skip
        if category in type_map and not type_map[category]:
            return None
        
        # Check quiet hours
        if prefs.quiet_hours_enabled and prefs.quiet_hours_start and prefs.quiet_hours_end:
            now = timezone.now().time()
            if prefs.quiet_hours_start <= now <= prefs.quiet_hours_end:
                # Quiet hours - only create if high priority or urgent
                if kwargs.get('priority', 'medium') not in ['high', 'urgent', 'critical']:
                    return None
        
        # Create notification
        notification = Notification(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )
        notification.save()
        
        return notification
    
    @staticmethod
    def get_user_from_profile(profile):
        """Get user from patient or doctor profile"""
        if hasattr(profile, 'profile'):
            return profile.profile.user
        return None


# ============================================
# SIGNAL RECEIVERS
# ============================================

# Appointment Signals
@receiver(post_save, sender='appointments.Appointment')
def handle_appointment_notification(sender, instance, created, **kwargs):
    """
    Send notifications when an appointment is created or updated.
    """
    from .models import Notification
    
    # ✅ Guard against None values
    if not instance.doctor_profile:
        # No doctor assigned yet, skip or send patient-only notification
        if created and instance.patient_profile:
            # Send notification to patient about pending appointment
            Notification.objects.create(
                user=instance.patient_profile.profile.user,
                title="Appointment Pending",
                message=f"Your appointment at {instance.clinic.name} is pending doctor assignment.",
                notification_type='appointment'
            )
        return
    
    if not instance.patient_profile:
        return
    
    doctor_user = None
    try:
        if instance.doctor_profile:
            doctor_user = instance.doctor_profile.profile.user
        patient_user = instance.patient_profile.profile.user
    except AttributeError:
        # Profile or user doesn't exist
        return
    
    if created:
        # New appointment created
        # Notify doctor
        if doctor_user:
            Notification.objects.create(
                user=doctor_user,
                title="New Appointment",
                message=f"New appointment with {patient_user.get_full_name()} on {instance.appointment_date} at {instance.start_time}",
                notification_type='appointment'
            )
        
        # Notify patient 
        Notification.objects.create(
            user=patient_user,
            title="Appointment Confirmed",
            message=f"Your appointment with has been scheduled for {instance.appointment_date} at {instance.start_time}" if not doctor_user else f"Your appointment with Dr. {doctor_user.get_full_name()}  has been scheduled for {instance.appointment_date} at {instance.start_time}",
            notification_type='appointment'
        )
    else:
        # Appointment updated
        if instance.status == 'confirmed':
            # Notify patient
            Notification.objects.create(
                user=patient_user,
                title="Appointment Confirmed",
                
                message=f"Your appointment with Dr. {instance.appointment_date} at {instance.start_time} has been confirmed" if not doctor_user else f"Your appointment with Dr. {doctor_user.get_full_name()}  has been scheduled for {instance.appointment_date} at {instance.start_time} has been confirmed",
                notification_type='appointment'
            )
        elif instance.status == 'cancelled':
            # Notify both
            Notification.objects.create(
                user=patient_user,
                title="Appointment Cancelled",
                # message=f"Your appointment with Dr. {doctor_user.get_full_name()} has been cancelled",
                message=f"Your appointment with Dr. {instance.appointment_date} at {instance.start_time} has been cancelled" if not doctor_user else f"Your appointment with Dr. {doctor_user.get_full_name()}  has been scheduled for {instance.appointment_date} at {instance.start_time}  has been cancelled", 
                notification_type='appointment'
            )
            if doctor_user:
                Notification.objects.create(
                    user=doctor_user,
                    title="Appointment Cancelled",
                    message=f"Appointment with {patient_user.get_full_name()} has been cancelled",
                    notification_type='appointment'
                )

# Consultation Signals
@receiver(post_save, sender='consultations.Consultation')
def handle_consultation_notification(sender, instance, created, **kwargs):
    """Create notifications for consultation events"""
    handler = NotificationSignalHandler()
    
    patient_user = instance.patient_profile.profile.user
    doctor_user = instance.doctor_profile.profile.user
    
    if created:
        # Consultation Started
        handler.create_notification(
            user=patient_user,
            notification_type='consultation_started',
            title='Consultation Started',
            message=f'Your consultation with Dr. {instance.doctor_profile.profile.user.get_full_name()} has started.',
            priority='high',
            related_object_id=str(instance.id),
            related_object_type='consultation',
            related_url=f'/consultations/{instance.id}/'
        )
        
        handler.create_notification(
            user=doctor_user,
            notification_type='consultation_started',
            title='Consultation Started',
            message=f'Consultation with {instance.patient_profile.profile.user.get_full_name()} has started.',
            priority='high',
            related_object_id=str(instance.id),
            related_object_type='consultation',
            related_url=f'/consultations/{instance.id}/'
        )
    
    elif instance.status == 'completed':
        # Consultation Completed
        handler.create_notification(
            user=patient_user,
            notification_type='consultation_completed',
            title='Consultation Completed',
            message=f'Your consultation with Dr. {instance.doctor_profile.profile.user.get_full_name()} has been completed.',
            priority='medium',
            related_object_id=str(instance.id),
            related_object_type='consultation',
            related_url=f'/consultations/{instance.id}/'
        )


# apps/chat/signals.py
# from chat.models import Conversation


# ============================================
# Chat Notification Signal - Fixed for Flask architecture
# ============================================
@receiver(post_save, sender='chat.Conversation')
def handle_conversation_notification(sender, instance, created, **kwargs):
    """
    Create notifications when a new conversation is created.
    """
    if not created:
        return
    
    handler = NotificationSignalHandler()
    
    # Notify patient
    patient_user = instance.patient_profile.profile.user
    doctor_user = instance.doctor_profile.profile.user
    
    # Notify patient
    handler.create_notification(
        user=patient_user,
        notification_type='chat_message',
        title='New Conversation Started',
        message=f'You have a new conversation with Dr. {doctor_user.get_full_name()}.',
        priority='medium',
        related_object_id=str(instance.conversation_id),
        related_object_type='chat',
        related_url=f'/chat/{instance.conversation_id}/'
    )
    
    # Notify doctor
    handler.create_notification(
        user=doctor_user,
        notification_type='chat_message',
        title='New Conversation Started',
        message=f'You have a new conversation with {patient_user.get_full_name()}.',
        priority='medium',
        related_object_id=str(instance.conversation_id),
        related_object_type='chat',
        related_url=f'/chat/{instance.conversation_id}/'
    )


@receiver(post_save, sender='chat.Conversation')
def handle_conversation_update_notification(sender, instance, created, **kwargs):
    """
    Create notifications when a conversation is updated (new message, etc.)
    """
    if created:
        return
    
    handler = NotificationSignalHandler()
    
    # Check if last message was updated (new message)
    if instance.last_message_preview and instance.last_message_sender:
        sender_user = instance.last_message_sender
        receiver_user = None
        
        # Determine receiver
        if sender_user == instance.patient_profile.profile.user:
            receiver_user = instance.doctor_profile.profile.user
        else:
            receiver_user = instance.patient_profile.profile.user
        
        if receiver_user and sender_user != receiver_user:
            sender_name = sender_user.get_full_name() or sender_user.username
            
            handler.create_notification(
                user=receiver_user,
                notification_type='chat_message',
                title='New Message',
                message=f'{sender_name}: {instance.last_message_preview[:100]}{"..." if len(instance.last_message_preview) > 100 else ""}',
                priority='medium',
                related_object_id=str(instance.conversation_id),
                related_object_type='chat',
                related_url=f'/chat/{instance.conversation_id}/',
                data={
                    'sender_id': sender_user.id,
                    'sender_name': sender_name,
                    'message_preview': instance.last_message_preview[:100],
                    'unread_count': instance.unread_count_patient if receiver_user == instance.patient_profile.profile.user else instance.unread_count_doctor
                }
            )


# ============================================
# Alternative: Flask Webhook Handler
# ============================================
# This function would be called by Flask when a new message arrives
def handle_flask_message_webhook(data):
    """
    Called by Flask chat server when a new message is received.
    This updates the Django Conversation model and creates notifications.
    """
    from django.utils import timezone
    from chat.models import Conversation
    # from apps.users.models import User
    
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    sender_id = data.get('sender_id')
    sender_name = data.get('sender_name')
    unread_count_patient = data.get('unread_count_patient', 0)
    unread_count_doctor = data.get('unread_count_doctor', 0)
    
    try:
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        
        # Update conversation with latest message
        conversation.last_message_preview = message[:255]
        conversation.last_message_at = timezone.now()
        
        # Update unread counts
        conversation.unread_count_patient = unread_count_patient
        conversation.unread_count_doctor = unread_count_doctor
        
        # Try to get sender user
        try:
            sender_user = User.objects.get(id=sender_id)
            conversation.last_message_sender = sender_user
        except User.DoesNotExist:
            pass
        
        conversation.save()
        
        # Create notification for receiver
        handler = NotificationSignalHandler()
        
        # Determine receiver
        if sender_user and sender_user == conversation.patient_profile.profile.user:
            receiver_user = conversation.doctor_profile.profile.user
            unread_count = unread_count_doctor
        else:
            receiver_user = conversation.patient_profile.profile.user
            unread_count = unread_count_patient
        
        if receiver_user and sender_user != receiver_user:
            sender_name_display = sender_name or sender_user.get_full_name() or sender_user.username
            
            handler.create_notification(
                user=receiver_user,
                notification_type='chat_message',
                title='New Message',
                message=f'{sender_name_display}: {message[:100]}{"..." if len(message) > 100 else ""}',
                priority='medium',
                related_object_id=str(conversation.conversation_id),
                related_object_type='chat',
                related_url=f'/chat/{conversation.conversation_id}/',
                data={
                    'sender_id': sender_user.id if sender_user else None,
                    'sender_name': sender_name_display,
                    'message_preview': message[:100],
                    'unread_count': unread_count
                }
            )
        
        return {'status': 'success', 'conversation_id': conversation_id}
        
    except Conversation.DoesNotExist:
        return {'status': 'error', 'message': 'Conversation not found'}


# ============================================
# Signal to clean up orphaned conversations
# ============================================
@receiver(post_save, sender='consultations.Consultation')
def handle_consultation_chat_cleanup(sender, instance, **kwargs):
    """
    When a consultation is cancelled or completed, optionally end the chat.
    """
    from chat.models import Conversation
    
    if instance.status in ['completed', 'cancelled']:
        # Find and end any active conversations
        conversations = Conversation.objects.filter(
            consultation=instance,
            is_active=True
        )
        
        for conversation in conversations:
            conversation.is_active = False
            conversation.ended_at = timezone.now()
            conversation.save()


# Prescription Signals
@receiver(post_save, sender='prescriptions.Prescription')
def handle_prescription_notification(sender, instance, created, **kwargs):
    """Create notifications for prescription events"""
    handler = NotificationSignalHandler()
    
    patient_user = instance.patient_profile.profile.user
    doctor_user = instance.doctor_profile.profile.user
    
    if created:
        # Prescription Created
        med_name = instance.medication_name
        handler.create_notification(
            user=patient_user,
            notification_type='prescription_created',
            title='New Prescription',
            message=f'A new prescription for {med_name} {instance.dosage} has been issued by Dr. {doctor_user.get_full_name()}.',
            priority='high',
            related_object_id=str(instance.id),
            related_object_type='prescription',
            related_url=f'/prescriptions/{instance.id}/'
        )
    
    elif instance.status == 'cancelled':
        # Prescription Cancelled
        handler.create_notification(
            user=patient_user,
            notification_type='prescription_cancelled',
            title='Prescription Cancelled',
            message=f'Your prescription for {instance.medication_name} has been cancelled.',
            priority='medium',
            related_object_id=str(instance.id),
            related_object_type='prescription',
            related_url=f'/prescriptions/{instance.id}/'
        )


# Lab Test Signals
@receiver(post_save, sender='labs.LabTestResult')
def handle_lab_result_notification(sender, instance, created, **kwargs):
    """Create notifications for lab results"""
    if not created:
        return
    
    handler = NotificationSignalHandler()
    
    patient_user = instance.order.patient_profile.profile.user
    doctor_user = instance.order.doctor_profile.profile.user
    
    test_name = instance.order.test_catalog.name
    
    if instance.is_critical:
        # Critical result - urgent notification
        handler.create_notification(
            user=doctor_user,
            notification_type='lab_critical',
            title='⚠️ CRITICAL LAB RESULT',
            message=f'CRITICAL: {test_name} result is {instance.result_value} for {patient_user.get_full_name()}. Immediate review required.',
            priority='critical',
            related_object_id=str(instance.id),
            related_object_type='lab_result',
            related_url=f'/labs/results/{instance.id}/'
        )
        
        handler.create_notification(
            user=patient_user,
            notification_type='lab_critical',
            title='⚠️ Critical Lab Result',
            message=f'Critical lab result detected for {test_name}. Your doctor will contact you shortly.',
            priority='critical',
            related_object_id=str(instance.id),
            related_object_type='lab_result',
            related_url=f'/labs/results/{instance.id}/'
        )
    
    elif instance.is_abnormal:
        # Abnormal result - high priority
        handler.create_notification(
            user=doctor_user,
            notification_type='lab_abnormal',
            title='Abnormal Lab Result',
            message=f'Abnormal {test_name} result ({instance.result_value}) for {patient_user.get_full_name()}. Please review.',
            priority='high',
            related_object_id=str(instance.id),
            related_object_type='lab_result',
            related_url=f'/labs/results/{instance.id}/'
        )
        
        handler.create_notification(
            user=patient_user,
            notification_type='lab_abnormal',
            title='Lab Result Available',
            message=f'Your {test_name} results are available. Please review with your doctor.',
            priority='medium',
            related_object_id=str(instance.id),
            related_object_type='lab_result',
            related_url=f'/labs/results/{instance.id}/'
        )
    else:
        # Normal result
        handler.create_notification(
            user=patient_user,
            notification_type='lab_results_ready',
            title='Lab Results Ready',
            message=f'Your {test_name} results are ready for review.',
            priority='low',
            related_object_id=str(instance.id),
            related_object_type='lab_result',
            related_url=f'/labs/results/{instance.id}/'
        )


# Queue Signals
@receiver(post_save, sender='appointments.QueueEntry')
def handle_queue_notification(sender, instance, created, **kwargs):
    """Create notifications for queue events"""
    handler = NotificationSignalHandler()
    
    patient_user = instance.patient_profile.profile.user
    # doctor_user = instance.doctor_profile.profile.user
    
    if created:
        # Patient added to queue
        handler.create_notification(
            user=patient_user,
            notification_type='queue_waiting',
            title='Added to Queue',
            message=f'You are in position {instance.queue_position} in the queue. Estimated wait: {instance.wait_time_minutes} minutes.',
            priority='medium',
            related_object_id=str(instance.id),
            related_object_type='queue',
            related_url='/queue/'
        )
    
    elif instance.status == 'admitted':
        # Patient admitted from queue
        handler.create_notification(
            user=patient_user,
            notification_type='queue_admitted',
            title='✅ Admitted from Queue',
            message=f'You have been admitted! Your consultation will begin shortly.',
            priority='high',
            related_object_id=str(instance.id),
            related_object_type='queue',
            related_url='/consultation/'
        )
    
    elif instance.queue_position != instance._original_queue_position:
        # Queue position updated
        handler.create_notification(
            user=patient_user,
            notification_type='queue_position_updated',
            title='Queue Position Updated',
            message=f'You are now at position {instance.queue_position}. Estimated wait: {instance.wait_time_minutes} minutes.',
            priority='low',
            related_object_id=str(instance.id),
            related_object_type='queue',
            related_url='/queue/'
        )


# Payment Signals
# @receiver(post_save, sender='payments.Payment')
# def handle_payment_notification(sender, instance, created, **kwargs):
#     """Create notifications for payment events"""
#     handler = NotificationSignalHandler()
    
#     patient_user = instance.patient_profile.profile.user
    
#     if instance.status == 'completed':
#         # Payment successful
#         handler.create_notification(
#             user=patient_user,
#             notification_type='payment_success',
#             title='Payment Successful ✅',
#             message=f'Your payment of ${instance.amount} has been processed successfully.',
#             priority='medium',
#             related_object_id=str(instance.id),
#             related_object_type='payment',
#             related_url=f'/payments/{instance.id}/'
#         )
    
#     elif instance.status == 'failed':
#         # Payment failed
#         handler.create_notification(
#             user=patient_user,
#             notification_type='payment_failed',
#             title='Payment Failed ❌',
#             message=f'Your payment of ${instance.amount} could not be processed. Please try again or update your payment method.',
#             priority='high',
#             related_object_id=str(instance.id),
#             related_object_type='payment',
#             related_url=f'/payments/{instance.id}/'
#         )
    
#     elif instance.status == 'refunded':
#         # Payment refunded
#         handler.create_notification(
#             user=patient_user,
#             notification_type='payment_refunded',
#             title='Payment Refunded',
#             message=f'Your payment of ${instance.amount} has been refunded.',
#             priority='medium',
#             related_object_id=str(instance.id),
#             related_object_type='payment',
#             related_url=f'/payments/{instance.id}/'
#         )


# Medical Record Signals
@receiver(post_save, sender='consultations.MedicalRecord')
def handle_medical_record_notification(sender, instance, created, **kwargs):
    """Create notifications for medical record updates"""
    if not created:
        handler = NotificationSignalHandler()
        patient_user = instance.patient_profile.profile.user
        
        handler.create_notification(
            user=patient_user,
            notification_type='record_updated',
            title='Medical Record Updated',
            message='Your medical record has been updated with new information.',
            priority='low',
            related_object_id=str(instance.id),
            related_object_type='medical_record',
            related_url=f'/medical-records/{instance.id}/'
        )


# User Signals
@receiver(post_save, sender=User)
def handle_user_notification(sender, instance, created, **kwargs):
    """Create welcome notification for new users"""
    if created:
        handler = NotificationSignalHandler()
        
        # Welcome notification
        handler.create_notification(
            user=instance,
            notification_type='info',
            title='Welcome to MHPro! 🎉',
            message='Welcome to your mental health journey. We\'re here to support you every step of the way.',
            priority='medium',
            related_url='/dashboard/'
        )
        
        # Create notification preferences
        NotificationPreference.objects.get_or_create(user=instance)