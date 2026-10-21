# apps/consultations/serializers.py
from rest_framework import serializers
from .models import (
    Consultation, 
    Examination, 
    PastMedicalHistory, 
    MedicalRecord,
    create_consultation_from_appointment,
    get_patient_full_medical_record
)
from accounts.models import PatientProfile, DoctorProfile
from appointments.serializers import AppointmentSerializer
from appointments.models import Appointment


class ExaminationSerializer(serializers.ModelSerializer):
    """Serializer for the Examination model"""
    
    examination_type_display = serializers.CharField(
        source='get_examination_type_display', 
        read_only=True
    )
    bmi = serializers.FloatField(read_only=True)
    is_vital_sign = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Examination
        fields = [
            'id', 'consultation', 'examination_type', 'examination_type_display',
            'findings', 'is_normal', 'notes', 'bp_systolic', 'bp_diastolic',
            'heart_rate', 'respiratory_rate', 'temperature', 'spo2',
            'weight', 'height', 'bmi', 'is_vital_sign',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'bmi', 'is_vital_sign')

# apps/consultations/serializers.py
from rest_framework import serializers
from .models import Consultation
from appointments.serializers import AppointmentSerializer


# class ConsultationSerializer(serializers.ModelSerializer):
#     type_display = serializers.CharField(source='get_type_display', read_only=True)
#     status_display = serializers.CharField(source='get_status_display', read_only=True)
#     patient_name = serializers.SerializerMethodField()
#     doctor_name = serializers.SerializerMethodField()
#     appointment_details = AppointmentSerializer(source='appointment', read_only=True)
#     is_doctor_assigned = serializers.BooleanField(read_only=True)

#     # ── Nested: prescriptions + labs tied to this consultation ──
#     prescriptions = serializers.SerializerMethodField()
#     lab_orders = serializers.SerializerMethodField()

#     appointment_id = serializers.PrimaryKeyRelatedField(
#         source='appointment',
#         queryset=Appointment.objects.all(),
#         write_only=True,
#         required=False,
#     )
#     patient_profile_id = serializers.PrimaryKeyRelatedField(
#         source='patient_profile',
#         queryset=PatientProfile.objects.all(),
#         write_only=True,
#         required=False,
#     )
#     doctor_profile_id = serializers.PrimaryKeyRelatedField(
#         source='doctor_profile',
#         queryset=DoctorProfile.objects.all(),
#         write_only=True,
#         required=False,
#     )

#     def get_doctor_name(self, obj):
#         if not obj.doctor_profile_id:
#             return None
#         user = obj.doctor_profile.profile.user
#         return f"Dr. {user.get_full_name() or user.email}"

#     class Meta:
#         model = Consultation
#         fields = [
#             'id', 'appointment', 'appointment_details',
#             'patient_profile', 'patient_name',
#             'doctor_profile', 'doctor_name', 'is_doctor_assigned',
#             'hpc', 'symptoms', 'duration', 'vitals', 'examinations',
#             'assessment', 'plan',
#             'type', 'type_display', 'status', 'status_display',
#             'clinic_location', 'chat_conversation_id',
#             'prescriptions', 'lab_orders',
#             'created_at', 'updated_at',
#         ]

#         read_only_fields = ('id', 'created_at', 'updated_at', 'chat_conversation_id')

#     # ── Computed fields ─────────────────────────────────────
#     def get_patient_name(self, obj):
#         return obj.patient_profile.profile.user.get_full_name()

#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"

#     def get_prescriptions(self, obj):
#         # Only fetch for detail views (retrieve/list on the frontend's EMR)
#         # If you want it on ALL list rows, drop the check below.
#         if not self.context.get('include_related', True):
#             return []

#         from prescriptions.serializers import PrescriptionSerializer
#         qs = obj.prescriptions.all().order_by('created_at')
#         return PrescriptionSerializer(qs, many=True, context=self.context).data

#     def get_lab_orders(self, obj):
#         if not self.context.get('include_related', True):
#             return []

#         from labs.serializers import LabTestOrderSerializer
#         qs = obj.lab_orders.all().order_by('created_at')
#         return LabTestOrderSerializer(qs, many=True, context=self.context).data

#     def create(self, validated_data):
#         if 'appointment' in validated_data:
#             appointment = validated_data.pop('appointment')
#             consultation = create_consultation_from_appointment(appointment)
#             for key, value in validated_data.items():
#                 setattr(consultation, key, value)
#             consultation.save()
#             return consultation
#         return super().create(validated_data)

# apps/consultations/serializers.py

class ConsultationSerializer(serializers.ModelSerializer):
    """Read serializer for Consultation."""

    type_display = serializers.CharField(
        source='get_type_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    appointment_details = AppointmentSerializer(
        source='appointment', read_only=True
    )

    # ✅ Nested data for the EMR
    prescriptions = serializers.SerializerMethodField()
    lab_orders = serializers.SerializerMethodField()

    class Meta:
        model = Consultation
        fields = [
            'id',
            'appointment', 'appointment_details',
            'patient_profile', 'patient_name',
            'doctor_profile', 'doctor_name',
            'hpc', 'symptoms', 'duration', 'vitals', 'examinations',
            'assessment', 'plan',
            'type', 'type_display',
            'status', 'status_display',
            'clinic_location', 'chat_conversation_id',
            'prescriptions', 'lab_orders',
            'created_at', 'updated_at',
        ]
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'chat_conversation_id',
        )

    def get_patient_name(self, obj):
        if not obj.patient_profile_id:
            return None
        user = obj.patient_profile.profile.user
        return user.get_full_name() or user.email

    def get_doctor_name(self, obj):
        # ✅ doctor may be None for instant consultations pre-admission
        if not obj.doctor_profile_id:
            return None
        user = obj.doctor_profile.profile.user
        return f"Dr. {user.get_full_name() or user.email}"

    def get_prescriptions(self, obj):
        if not self.context.get('include_related', True):
            return []
        from prescriptions.serializers import PrescriptionSerializer
        qs = obj.prescriptions.all().order_by('created_at')
        return PrescriptionSerializer(qs, many=True, context=self.context).data

    def get_lab_orders(self, obj):
        if not self.context.get('include_related', True):
            return []
        from labs.serializers import LabTestOrderSerializer
        qs = obj.lab_orders.all().order_by('created_at')
        return LabTestOrderSerializer(qs, many=True, context=self.context).data

# apps/consultations/serializers.py
from rest_framework import serializers
from .models import Consultation
from accounts.models import Profile, PatientProfile, DoctorProfile


class ConsultationCreateSerializer(serializers.Serializer):
    """
    Create a consultation using mh_user_id + doctor_id.
    Everything else (patient_profile, doctor_profile) is auto-resolved.
    """
    mh_user_id = serializers.CharField(required=True)
    doctor_id = serializers.IntegerField(required=False, allow_null=True)

    # Clinical fields
    hpc = serializers.CharField(required=False, allow_blank=True)
    symptoms = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.CharField(required=False, allow_blank=True)
    vitals = serializers.CharField(required=False, allow_blank=True)
    examinations = serializers.CharField(required=False, allow_blank=True)  # ← ADD
    assessment = serializers.CharField(required=False, allow_blank=True)
    plan = serializers.CharField(required=False, allow_blank=True)

    type = serializers.ChoiceField(
        choices=Consultation.TYPE_CHOICES, default='virtual'
    )
    clinic_location = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        request = self.context['request']
        mh_user_id = validated_data.pop('mh_user_id')

        # Strip anything the client might have sent that we don't trust
        validated_data.pop('patient_profile', None)
        validated_data.pop('doctor_profile', None)
        validated_data.pop('appointment', None)
        validated_data.pop('appointment_id', None)
        validated_data.pop('doctor_id', None)

        # 1. Resolve Profile → PatientProfile (auto-create)
        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            raise serializers.ValidationError(
                {"mh_user_id": f"Profile '{mh_user_id}' not found"}
            )

        patient_profile = getattr(profile, 'patient_profile', None)
        if patient_profile is None:
            patient_profile = PatientProfile.objects.create(profile=profile)

        # 2. Resolve doctor from request.user
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile:
            raise serializers.ValidationError(
                {"detail": "No doctor attached to your account."}
            )

        # 3. Reuse an existing ongoing consultation if present
        existing = Consultation.objects.filter(
            patient_profile=patient_profile,
            doctor_profile=doctor_profile,
            status='ongoing',
        ).order_by('-created_at').first()

        if existing:
            for field in [
                'hpc',
                'symptoms',
                'duration',
                'vitals',
                'examinations',        # ← ADD
                'assessment',
                'plan',
                'type',
                'clinic_location',
            ]:
                if field in validated_data:
                    setattr(existing, field, validated_data[field])
            existing.save()
            return existing

        # 4. Otherwise create a fresh consultation
        return Consultation.objects.create(
            patient_profile=patient_profile,
            doctor_profile=doctor_profile,
            status='ongoing',
            **validated_data,
        )
        

class ConsultationCompleteSerializer(serializers.Serializer):
    """Serializer for completing a consultation"""
    
    consultation_id = serializers.IntegerField(required=True)
    
    def validate_consultation_id(self, value):
        try:
            consultation = Consultation.objects.get(id=value)
            if consultation.status == 'completed':
                raise serializers.ValidationError("Consultation is already completed")
            if consultation.status == 'cancelled':
                raise serializers.ValidationError("Cannot complete a cancelled consultation")
            return value
        except Consultation.DoesNotExist:
            raise serializers.ValidationError("Consultation not found")
    
    def update(self, instance, validated_data):
        instance.complete()
        return instance


# apps/consultations/serializers.py
from rest_framework import serializers
from .models import PastMedicalHistory


# apps/consultations/serializers.py
from rest_framework import serializers
from .models import PastMedicalHistory

# apps/consultations/serializers.py
from rest_framework import serializers
from .models import PastMedicalHistory


class PastMedicalHistorySerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()
    history_type_display = serializers.CharField(
        source='get_history_type_display', read_only=True
    )
    mh_user_id = serializers.SerializerMethodField()

    class Meta:
        model = PastMedicalHistory
        fields = [
            'id',
            'patient_profile',      # writable — the view sets this
            'mh_user_id',           # readable — the patient's mh_user_id
            'patient_name',
            'history_type',
            'history_type_display',
            'content',
            'notes',
            'recorded_by',
            'recorded_by_name',
            'recorded_date',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = (
            'id',
            'recorded_by',
            'recorded_date',
            'created_at',
            'updated_at',
        )

    def get_mh_user_id(self, obj):
        return obj.patient_profile.profile.mh_user_id

    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return f"Dr. {obj.recorded_by.profile.user.get_full_name()}"
        return None

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            if hasattr(request.user.profile, 'doctor_profile'):
                validated_data['recorded_by'] = request.user.profile.doctor_profile
        return super().create(validated_data)
    

class MedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer for the MedicalRecord model"""
    
    patient_name = serializers.SerializerMethodField()
    last_updated_by_name = serializers.SerializerMethodField()
    
    # Nested data for comprehensive view
    demographic_info = serializers.DictField(read_only=True)
    all_consultations = ConsultationSerializer(many=True, read_only=True)
    past_medical_histories = PastMedicalHistorySerializer(many=True, read_only=True)
    vitals_history = serializers.ListField(read_only=True)
    recent_consultations = ConsultationSerializer(many=True, read_only=True)
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient_profile', 'patient_name', 'record_number',
            'last_updated_by', 'last_updated_by_name',
            'active_problems', 'active_medications_summary', 
            'allergies_summary', 'is_complete', 'last_review_date',
            'demographic_info', 'all_consultations', 'past_medical_histories',
            'vitals_history', 'recent_consultations',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'record_number')
    
    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    
    def get_last_updated_by_name(self, obj):
        if obj.last_updated_by:
            return f"Dr. {obj.last_updated_by.profile.user.get_full_name()}"
        return None


class PatientFullMedicalRecordSerializer(serializers.Serializer):
    """Serializer for the complete patient medical record"""
    
    medical_record = MedicalRecordSerializer()
    consultations = ConsultationSerializer(many=True)
    past_medical_histories = PastMedicalHistorySerializer(many=True)
    examinations = ExaminationSerializer(many=True)