# apps/chat/serializers.py
from rest_framework import serializers
from .models import Conversation, ChatSyncLog, PendingMessageSync
from accounts.models import PatientProfile, DoctorProfile


# apps/chat/serializers.py
from rest_framework import serializers
from .models import Conversation
from accounts.models import Profile, PatientProfile
from consultations.models import Consultation


class ConversationSerializer(serializers.ModelSerializer):
    """Read serializer"""
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    mh_user_id = serializers.SerializerMethodField()
    consultation_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Conversation
        fields = [
            'id',
            'conversation_id',
            'consultation', 'consultation_id',
            'mh_user_id',
            'patient_name',
            'doctor_name',
            'is_active',
            'started_at',
            'ended_at',
            'created_at',
            'updated_at',
        ]

    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()

    def get_doctor_name(self, obj):
        if obj.doctor_profile:
            return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
        return None

    def get_mh_user_id(self, obj):
        return obj.patient_profile.profile.mh_user_id


# apps/chat/serializers.py
import uuid
from rest_framework import serializers
from .models import Conversation
from accounts.models import Profile, PatientProfile
from consultations.models import Consultation


class ConversationCreateSerializer(serializers.Serializer):
    mh_user_id = serializers.CharField(required=True)
    consultation_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def create(self, validated_data):
        request = self.context['request']
        mh_user_id = validated_data.pop('mh_user_id')
        consultation_id = validated_data.pop('consultation_id', None)

        # 1. Patient
        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            raise serializers.ValidationError(
                {"mh_user_id": f"Profile '{mh_user_id}' not found"}
            )

        patient_profile = getattr(profile, 'patient_profile', None)
        if patient_profile is None:
            patient_profile = PatientProfile.objects.create(profile=profile)

        # 2. Doctor
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile:
            raise serializers.ValidationError(
                {"detail": "Only doctors can start a conversation."}
            )

        # 3. Consultation (optional)
        consultation = None
        if consultation_id:
            try:
                consultation = Consultation.objects.get(id=consultation_id)
            except Consultation.DoesNotExist:
                raise serializers.ValidationError(
                    {"consultation_id": f"Consultation {consultation_id} not found"}
                )
            if consultation.patient_profile != patient_profile:
                raise serializers.ValidationError(
                    {"consultation_id": "Consultation does not belong to this patient"}
                )

        # 4. Reuse active conversation if it exists
        existing = Conversation.objects.filter(
            patient_profile=patient_profile,
            doctor_profile=doctor_profile,
            consultation=consultation,
            is_active=True,
        ).first()
        if existing:
            return existing

        # 5. Generate the UUID explicitly
        new_id = str(uuid.uuid4())

        # Double-check uniqueness (extremely unlikely to collide)
        while Conversation.objects.filter(conversation_id=new_id).exists():
            new_id = str(uuid.uuid4())

        return Conversation.objects.create(
            conversation_id=new_id,
            patient_profile=patient_profile,
            doctor_profile=doctor_profile,
            consultation=consultation,
            is_active=validated_data.get('is_active', True),
        )
        
class ConversationDetailSerializer(ConversationSerializer):
    """
    Detailed Conversation Serializer with unread counts per user
    """
    unread_count = serializers.SerializerMethodField()
    
    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields 
    
    def get_unread_count(self, obj):
        user = self.context.get('request').user
        if user == obj.patient_profile.profile.user:
            return obj.unread_count_patient
        elif user == obj.doctor_profile.profile.user:
            return obj.unread_count_doctor
        return 0


class ChatSyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer for Chat Sync Log
    """
    conversation_id = serializers.CharField(source='conversation.conversation_id', read_only=True)
    
    class Meta:
        model = ChatSyncLog
        fields = (
            'id',
            'conversation',
            'conversation_id',
            'sync_type',
            'flask_conversation_id',
            'details',
            'synced_at',
            'is_successful',
            'error_message',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('synced_at', 'created_at', 'updated_at')


class PendingMessageSyncSerializer(serializers.ModelSerializer):
    """
    Serializer for Pending Message Sync
    """
    conversation_id = serializers.CharField(source='conversation.conversation_id', read_only=True)
    
    class Meta:
        model = PendingMessageSync
        fields = (
            'id',
            'conversation',
            'conversation_id',
            'message_data',
            'attempt_count',
            'max_attempts',
            'last_attempt',
            'is_processed',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')