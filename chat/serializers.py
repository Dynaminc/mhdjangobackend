# apps/chat/serializers.py
from rest_framework import serializers
from .models import Conversation, ChatSyncLog, PendingMessageSync
from accounts.models import PatientProfile, DoctorProfile


# apps/chat/serializers.py
from rest_framework import serializers
from .models import Conversation
from accounts.models import Profile, PatientProfile
from consultations.models import Consultation


# apps/chat/serializers.py
class ConversationSerializer(serializers.ModelSerializer):
    """Read serializer"""

    patient_id = serializers.SerializerMethodField()
    doctor_id  = serializers.SerializerMethodField()

    patient_name = serializers.SerializerMethodField()
    doctor_name  = serializers.SerializerMethodField()
    mh_user_id   = serializers.SerializerMethodField()

    consultation_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Conversation
        fields = [
            'id',
            'conversation_id',
            'consultation', 'consultation_id',
            'mh_user_id',
            'patient_id',        # ← new
            'doctor_id',         # ← new
            'patient_name',
            'doctor_name',
            'is_active',
            'started_at',
            'ended_at',
            'created_at',
            'updated_at',
        ]

    # ─── ids ─────────────────────────────────────────────
    def get_patient_id(self, obj):
        try:
            return obj.patient_profile.profile.user_id
        except AttributeError:
            return None

    def get_doctor_id(self, obj):
        try:
            return obj.doctor_profile.profile.user_id
        except AttributeError:
            return None

    # ─── names ───────────────────────────────────────────
    def get_patient_name(self, obj):
        try:
            return obj.patient_profile.profile.user.get_full_name()
        except AttributeError:
            return None

    def get_doctor_name(self, obj):
        try:
            return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
        except AttributeError:
            return None

    def get_mh_user_id(self, obj):
        try:
            return obj.patient_profile.profile.mh_user_id
        except AttributeError:
            return None
        
# class ConversationSerializer(serializers.ModelSerializer):
#     """Read serializer"""
#     patient_name = serializers.SerializerMethodField()
#     doctor_name = serializers.SerializerMethodField()
#     patient_id = serializers.IntegerField(source='patient_profile.profile.user_id', read_only=True)
#     doctor_id  = serializers.IntegerField(source='doctor_profile.profile.user_id',  read_only=True)
    
#     # patient_id = serializers.IntegerField(
#     #     source='patient_profile.user.id', read_only=True
#     # )
#     # doctor_id = serializers.IntegerField(
#     #     source='doctor_profile.user.id', read_only=True
#     # )
#     mh_user_id = serializers.SerializerMethodField()
#     consultation_id = serializers.IntegerField(read_only=True, allow_null=True)

#     class Meta:
#         model = Conversation
#         fields = [
#             'id',
#             'conversation_id',
#             'consultation', 'consultation_id',
#             'mh_user_id',            
#             'patient_id',        # ← new
#             'doctor_id',         # ← new
#             'patient_name',
#             'doctor_name',
#             'is_active',
#             'started_at',
#             'ended_at',
#             'created_at',
#             'updated_at',
#         ]

#     def get_patient_name(self, obj):
#         return obj.patient_profile.profile.user.get_full_name()

#     def get_doctor_name(self, obj):
#         if obj.doctor_profile:
#             return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
#         return None

#     def get_mh_user_id(self, obj):
#         return obj.patient_profile.profile.mh_user_id


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

        # 2. Doctor (caller must be a doctor)
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile:
            raise serializers.ValidationError(
                {"detail": "Only doctors can start a conversation."}
            )

        # 3. Optional consultation (validated, not required)
        consultation = None
        if consultation_id:
            try:
                consultation = Consultation.objects.get(id=consultation_id)
            except Consultation.DoesNotExist:
                raise serializers.ValidationError(
                    {"consultation_id": f"Consultation {consultation_id} not found"}
                )
            if consultation.patient_profile_id != patient_profile.id:
                raise serializers.ValidationError(
                    {"consultation_id": "Consultation does not belong to this patient"}
                )

        # 4. ★ Reuse ANY active conversation between this patient and doctor.
        #    Do not include `consultation` in the filter — None vs non-None
        #    should not force a new row.
        existing = (
            Conversation.objects
            .filter(
                patient_profile=patient_profile,
                doctor_profile=doctor_profile,
                is_active=True,
            )
            .order_by('-created_at')
            .first()
        )
        if existing:
            # Optional: attach the consultation if the row didn't have one.
            if consultation and existing.consultation_id is None:
                existing.consultation = consultation
                existing.save(update_fields=['consultation', 'updated_at'])
            return existing

        # 5. Create a new one
        return Conversation.objects.create(
            conversation_id=str(uuid.uuid4()),
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