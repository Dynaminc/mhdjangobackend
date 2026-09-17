# apps/prescriptions/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    MedicationCatalog,
    Prescription,
    RefillRequest,
    MedicationInteraction,
    MedicationSchedule,
    MedicationAdherence
)
from accounts.models import PatientProfile, DoctorProfile
from consultations.models import Consultation, MedicalRecord
from consultations.serializers import ConsultationSerializer, MedicalRecordSerializer
# apps/prescriptions/serializers.py
from rest_framework import serializers
from .models import Prescription
from accounts.models import Profile, PatientProfile

# apps/prescriptions/serializers.py
from rest_framework import serializers
from .models import Prescription
from accounts.models import Profile, PatientProfile


class PrescriptionSerializer(serializers.ModelSerializer):
    """Read serializer for Prescription"""
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    mh_user_id = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    frequency_display = serializers.CharField(read_only=True)
    duration_display = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Prescription
        fields = [
            'id', 'prescription_number',
            'mh_user_id', 'patient_name', 'doctor_name',
            'medication_name', 'dosage',
            'frequency', 'frequency_display', 'frequency_custom',
            'duration_value', 'duration_unit', 'duration_display',
            'quantity', 'refills', 'refills_used',
            'instructions', 'additional_notes',
            'prescribed_date', 'start_date', 'expiry_date', 'last_filled_date',
            'status', 'status_display', 'is_active',
            'pharmacy_name', 'pharmacy_phone', 'pharmacy_address',
            'created_at', 'updated_at',
        ]

    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"

    def get_mh_user_id(self, obj):
        return obj.patient_profile.profile.mh_user_id


class PrescriptionCreateSerializer(serializers.Serializer):
    """Write serializer — accepts `mh_user_id` and auto-resolves the rest"""
    mh_user_id = serializers.CharField(required=True)

    medication_name = serializers.CharField()
    dosage = serializers.CharField()
    frequency = serializers.ChoiceField(choices=Prescription.FREQUENCY_CHOICES)
    frequency_custom = serializers.CharField(required=False, allow_blank=True)

    duration_value = serializers.IntegerField(required=False, default=30)
    duration_unit = serializers.ChoiceField(
        choices=Prescription.DURATION_UNIT_CHOICES,
        required=False, default='days'
    )

    quantity = serializers.IntegerField()
    refills = serializers.IntegerField(required=False, default=0)

    instructions = serializers.CharField(required=False, allow_blank=True)
    additional_notes = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)

    pharmacy_name = serializers.CharField(required=False, allow_blank=True)
    pharmacy_phone = serializers.CharField(required=False, allow_blank=True)
    pharmacy_address = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        request = self.context['request']
        mh_user_id = validated_data.pop('mh_user_id')

        # 1. Resolve Profile → PatientProfile (auto-create if missing)
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
        
        if request.user.profile.role != 'doctor':
            raise serializers.ValidationError(
                {"detail": "User not doctor"}
            )
        if not doctor_profile:
            doctor_profile = DoctorProfile.objects.create(profile=request.user.profile)
            # raise serializers.ValidationError(
            #     {"detail": "Only doctors can create prescriptions."}
            # )

        # 3. Create the prescription
        return Prescription.objects.create(
            patient_profile=patient_profile,
            doctor_profile=doctor_profile,
            status='active',
            **validated_data,
        )
        
        

class MedicationCatalogSerializer(serializers.ModelSerializer):
    """Serializer for the MedicationCatalog model"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    form_display = serializers.CharField(source='get_form_display', read_only=True)
    schedule_display = serializers.CharField(source='get_schedule_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = MedicationCatalog
        fields = [
            'id', 'code', 'name', 'brand_name', 'category', 'category_display',
            'full_name', 'form', 'form_display', 'route_of_administration',
            'default_dosage', 'dosage_unit', 'dosage_form', 'strength',
            'concentration', 'schedule', 'schedule_display',
            'is_controlled', 'requires_prescription',
            'contraindications', 'warnings', 'side_effects', 'interactions',
            'pregnancy_category', 'breastfeeding_safety',
            'average_cost', 'is_active', 'requires_monitoring',
            'monitoring_tests', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class MedicationCatalogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing medications"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = MedicationCatalog
        fields = [
            'id', 'code', 'name', 'brand_name', 'full_name',
            'category', 'category_display', 'form',
            'is_controlled', 'requires_prescription', 'is_active'
        ]


class MedicationScheduleSerializer(serializers.ModelSerializer):
    """Serializer for MedicationSchedule model"""
    
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = MedicationSchedule
        fields = [
            'id', 'prescription', 'day_of_week', 'day_display',
            'time', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class MedicationAdherenceSerializer(serializers.ModelSerializer):
    """Serializer for MedicationAdherence model"""
    
    patient_name = serializers.SerializerMethodField()
    medication_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicationAdherence
        fields = [
            'id', 'prescription', 'patient_profile', 'patient_name',
            'medication_name', 'date', 'taken', 'time_taken',
            'skipped_reason', 'side_effects', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    
    def get_medication_name(self, obj):
        return obj.prescription.medication_name



class PrescriptionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing prescriptions"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    medication_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'prescription_number', 'patient_name', 'doctor_name',
            'medication_name', 'dosage', 'status', 'status_display',
            'prescribed_date', 'expiry_date', 'refills', 'refills_used'
        ]
    
    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"


class PrescriptionCreateSerializdzdzer(serializers.ModelSerializer):
    """Serializer for creating prescriptions"""
    
    class Meta:
        model = Prescription
        fields = [
            'consultation', 'medical_record', 'patient_profile',
            'medication', 'custom_medication_name', 'dosage',
            'frequency', 'frequency_custom', 'duration_value',
            'duration_unit', 'quantity', 'refills',
            'instructions', 'additional_notes', 'start_date',
            'pharmacy_name', 'pharmacy_phone', 'pharmacy_address',
            'is_eprescribing', 'eprescribing_id'
        ]
    
    def create(self, validated_data):
        # Set doctor_profile from request user
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            if hasattr(request.user.profile, 'doctor_profile'):
                validated_data['doctor_profile'] = request.user.profile.doctor_profile
        
        # Set default status
        validated_data['status'] = 'active'
        
        return super().create(validated_data)


class PrescriptionWithSchedulesSerializer(PrescriptionSerializer):
    """Detailed serializer for prescription with schedules"""
    
    schedules = MedicationScheduleSerializer(many=True, read_only=True)
    
    class Meta(PrescriptionSerializer.Meta):
        fields = PrescriptionSerializer.Meta.fields


class PrescriptionRefillSerializer(serializers.Serializer):
    """Serializer for refilling a prescription"""
    
    prescription_id = serializers.IntegerField(required=True)
    
    def validate_prescription_id(self, value):
        try:
            prescription = Prescription.objects.get(id=value)
            if not prescription.can_refill():
                raise serializers.ValidationError(
                    "This prescription cannot be refilled"
                )
            return value
        except Prescription.DoesNotExist:
            raise serializers.ValidationError("Prescription not found")


class PrescriptionStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating prescription status"""
    
    status = serializers.ChoiceField(choices=Prescription.STATUS_CHOICES, required=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class RefillRequestSerializer(serializers.ModelSerializer):
    """Serializer for the RefillRequest model"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    patient_name = serializers.SerializerMethodField()
    medication_name = serializers.SerializerMethodField()
    prescription_number = serializers.CharField(source='prescription.prescription_number', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = RefillRequest
        fields = [
            'id', 'prescription', 'prescription_number', 'patient_profile',
            'patient_name', 'medication_name', 'status', 'status_display',
            'reason', 'notes', 'requested_date', 'reviewed_date',
            'reviewed_by', 'reviewed_by_name', 'review_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'requested_date', 'reviewed_date', 'created_at', 'updated_at')
    
    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    
    def get_medication_name(self, obj):
        return obj.prescription.medication_name
    
    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return f"Dr. {obj.reviewed_by.profile.user.get_full_name()}"
        return None


class RefillRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating refill requests"""
    
    class Meta:
        model = RefillRequest
        fields = ['prescription', 'reason', 'notes']
    
    def validate(self, data):
        prescription = data.get('prescription')
        if not prescription.can_refill():
            raise serializers.ValidationError(
                "This prescription cannot be refilled"
            )
        return data


class RefillRequestApproveSerializer(serializers.Serializer):
    """Serializer for approving refill requests"""
    
    approved = serializers.BooleanField(required=True)
    review_notes = serializers.CharField(required=False, allow_blank=True)


class MedicationInteractionSerializer(serializers.ModelSerializer):
    """Serializer for the MedicationInteraction model"""
    
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    medication_a_name = serializers.CharField(source='medication_a.name', read_only=True)
    medication_b_name = serializers.CharField(source='medication_b.name', read_only=True)
    medication_a_code = serializers.CharField(source='medication_a.code', read_only=True)
    medication_b_code = serializers.CharField(source='medication_b.code', read_only=True)
    
    class Meta:
        model = MedicationInteraction
        fields = [
            'id', 'medication_a', 'medication_a_name', 'medication_a_code',
            'medication_b', 'medication_b_name', 'medication_b_code',
            'severity', 'severity_display', 'description',
            'mechanism', 'management', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class MedicationAdherenceStatsSerializer(serializers.Serializer):
    """Serializer for medication adherence statistics"""
    
    total_days = serializers.IntegerField()
    days_taken = serializers.IntegerField()
    adherence_rate = serializers.FloatField()
    missed_days = serializers.ListField(child=serializers.DateField())
    side_effects_reported = serializers.ListField(child=serializers.CharField())


class MedicationSearchSerializer(serializers.Serializer):
    """Serializer for medication search"""
    
    query = serializers.CharField(required=True)
    category = serializers.CharField(required=False)
    is_controlled = serializers.BooleanField(required=False)
    requires_prescription = serializers.BooleanField(required=False)