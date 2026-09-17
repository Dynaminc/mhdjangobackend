# apps/chat/models.py
from django.db import models
from accounts.models import BaseModel, Profile, DoctorProfile, PatientProfile
import uuid


class Conversation(BaseModel):
    """
    Chat conversation metadata only.
    Actual messages are stored in Flask.
    """
    
    # Unique identifier (matches Flask conversation_id)
    conversation_id = models.CharField(
        max_length=36, 
        unique=True, 
        db_index=True,
        blank=True,          # allow blank in forms (Django), we set it in save()
        editable=False,      # 👈 makes admin/forms not require it
    )
    
    # Reference to consultation (if from a consultation)
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_conversation'
    )
    
    # Participants (through profiles)
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='chat_conversations_as_patient'
    )
    doctor_profile = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='chat_conversations_as_doctor'
    )
    
    # Conversation status
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Denormalized fields from Flask (for quick display)
    last_message_preview = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Short preview of last message (synced from Flask)"
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_sender = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    # Unread counts (synced from Flask or managed by Django)
    unread_count_patient = models.IntegerField(default=0)
    unread_count_doctor = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())
        super().save(*args, **kwargs)
        
    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        doctor_name = self.doctor_profile.profile.user.get_full_name()
        return f"Conv {self.conversation_id[:8]} - {patient_name} ↔ {doctor_name}"
    
    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        if self.patient_profile.profile.user == user:
            return self.doctor_profile.profile.user
        return self.patient_profile.profile.user
    
    class Meta:
        indexes = [
            models.Index(fields=['conversation_id']),
            models.Index(fields=['patient_profile', 'is_active']),
            models.Index(fields=['doctor_profile', 'is_active']),
            models.Index(fields=['consultation']),
        ]


# ============================================
# Sync Log (to track sync status with Flask)
# ============================================
class ChatSyncLog(BaseModel):
    """
    Track when Django syncs with Flask chat server.
    """
    
    SYNC_TYPES = (
        ('conversation_created', 'Conversation Created'),
        ('message_received', 'Message Received'),
        ('status_update', 'Status Update'),
        ('full_sync', 'Full Sync'),
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='sync_logs'
    )
    sync_type = models.CharField(max_length=50, choices=SYNC_TYPES)
    flask_conversation_id = models.CharField(max_length=36)
    details = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.conversation.conversation_id}"


# ============================================
# Message Sync Queue (for offline support)
# ============================================
class PendingMessageSync(BaseModel):
    """
    Queue for messages that need to be synced with Flask.
    """
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='pending_syncs'
    )
    message_data = models.JSONField()
    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    last_attempt = models.DateTimeField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Pending sync for {self.conversation.conversation_id}"