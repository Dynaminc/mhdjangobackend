# apps/labs/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    LabTestCatalog,
    LabTestOrder,
    LabTestResult,
    LabTestAttachment,
    LabPanel,
    LabTestProfile,
    LabOrderTemplate
)
from accounts.models import PatientProfile, DoctorProfile
from consultations.models import Consultation, MedicalRecord
from consultations.serializers import ConsultationSerializer, MedicalRecordSerializer


class LabTestCatalogSerializer(serializers.ModelSerializer):
    """Serializer for the LabTestCatalog model"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    sample_type_display = serializers.CharField(source='get_sample_type_display', read_only=True)
    
    class Meta:
        model = LabTestCatalog
        fields = [
            'id', 'code', 'name', 'short_name', 'category', 'category_display',
            'sample_type', 'sample_type_display', 'sample_volume', 'sample_container',
            'fasting_required', 'fasting_hours',
            'reference_range_male', 'reference_range_female', 'reference_range_child',
            'unit', 'cost', 'turnaround_time_hours',
            'is_active', 'requires_authorization', 'requires_consent',
            'description', 'clinical_indications', 'interpretation_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class LabTestCatalogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing lab tests"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = LabTestCatalog
        fields = [
            'id', 'code', 'name', 'short_name', 'category', 'category_display',
            'cost', 'turnaround_time_hours', 'is_active'
        ]


class LabTestResultSerializer(serializers.ModelSerializer):
    """Serializer for the LabTestResult model"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verified_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    test_name = serializers.CharField(source='order.test_catalog.name', read_only=True)
    
    class Meta:
        model = LabTestResult
        fields = [
            'id', 'order', 'order_number', 'test_name',
            'result_value', 'result_numeric', 'unit', 'reference_range',
            'is_abnormal', 'is_critical', 'is_high', 'is_low',
            'result_text', 'interpretation', 'status', 'status_display',
            'is_verified', 'verified_by', 'verified_by_name',
            'verified_at', 'comments', 'reviewed_at', 'reviewed_by',
            'reviewed_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return f"Dr. {obj.verified_by.profile.user.get_full_name()}"
        return None
    
    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return f"Dr. {obj.reviewed_by.profile.user.get_full_name()}"
        return None


class LabTestAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for the LabTestAttachment model"""
    
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = LabTestAttachment
        fields = [
            'id', 'result', 'file', 'file_url', 'file_name', 'file_size',
            'mime_type', 'uploaded_by', 'uploaded_by_name',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return f"Dr. {obj.uploaded_by.profile.user.get_full_name()}"
        return None
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


# class LabTestOrderSerializer(serializers.ModelSerializer):
#     """Serializer for the LabTestOrder model"""
    
#     priority_display = serializers.CharField(source='get_priority_display', read_only=True)
#     status_display = serializers.CharField(source='get_status_display', read_only=True)
#     patient_name = serializers.SerializerMethodField()
#     doctor_name = serializers.SerializerMethodField()
#     test_name = serializers.CharField(source='test_catalog.name', read_only=True)
#     test_code = serializers.CharField(source='test_catalog.code', read_only=True)
    
#     # Nested serializers for detailed views
#     test_details = LabTestCatalogSerializer(source='test_catalog', read_only=True)
#     results = LabTestResultSerializer(many=True, read_only=True)
#     consultation_details = ConsultationSerializer(source='consultation', read_only=True)
#     medical_record_details = MedicalRecordSerializer(source='medical_record', read_only=True)
    
#     # For create/update operations
#     test_catalog_id = serializers.PrimaryKeyRelatedField(
#         source='test_catalog',
#         queryset=LabTestCatalog.objects.filter(is_active=True),
#         write_only=True,
#         required=True
#     )
#     patient_profile_id = serializers.PrimaryKeyRelatedField(
#         source='patient_profile',
#         queryset=PatientProfile.objects.all(),
#         write_only=True,
#         required=True
#     )
#     doctor_profile_id = serializers.PrimaryKeyRelatedField(
#         source='doctor_profile',
#         queryset=DoctorProfile.objects.all(),
#         write_only=True,
#         required=False
#     )
#     consultation_id = serializers.PrimaryKeyRelatedField(
#         source='consultation',
#         queryset=Consultation.objects.all(),
#         write_only=True,
#         required=False,
#         allow_null=True
#     )
#     medical_record_id = serializers.PrimaryKeyRelatedField(
#         source='medical_record',
#         queryset=MedicalRecord.objects.all(),
#         write_only=True,
#         required=True
#     )
#     authorized_by_id = serializers.PrimaryKeyRelatedField(
#         source='authorized_by',
#         queryset=DoctorProfile.objects.all(),
#         write_only=True,
#         required=False,
#         allow_null=True
#     )
    
#     class Meta:
#         model = LabTestOrder
#         fields = [
#             'id', 'order_number', 'consultation', 'consultation_id',
#             'consultation_details', 'medical_record', 'medical_record_id',
#             'medical_record_details', 'patient_profile', 'patient_profile_id',
#             'patient_name', 'doctor_profile', 'doctor_profile_id',
#             'doctor_name', 'test_catalog', 'test_catalog_id',
#             'test_name', 'test_code', 'test_details',
#             'priority', 'priority_display', 'status', 'status_display',
#             'ordered_date', 'collected_date', 'completed_date', 'cancelled_date',
#             'collection_instructions', 'collection_location',
#             'clinical_notes', 'clinical_indication',
#             'authorized_by', 'authorized_by_id', 'authorized_at',
#             'consent_obtained', 'consent_obtained_at',
#             'results', 'created_at', 'updated_at'
#         ]
#         read_only_fields = (
#             'id', 'order_number', 'ordered_date', 'completed_date',
#             'cancelled_date', 'authorized_at', 'created_at', 'updated_at'
#         )
    
#     def get_patient_name(self, obj):
#         return obj.patient_profile.profile.user.get_full_name()
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
    
#     def validate(self, data):
#         # If consultation is provided, ensure it matches patient
#         consultation = data.get('consultation')
#         patient_profile = data.get('patient_profile')
#         if consultation and patient_profile:
#             if consultation.patient_profile != patient_profile:
#                 raise serializers.ValidationError(
#                     "Consultation patient does not match patient_profile"
#                 )
#         return data


class LabTestOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing lab orders"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    test_name = serializers.CharField(source='test_catalog.name', read_only=True)
    
    class Meta:
        model = LabTestOrder
        fields = [
            'id', 'order_number', 'patient_name', 'doctor_name',
            'test_name', 'priority', 'status', 'status_display',
            'ordered_date', 'completed_date'
        ]
    
    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"


# class LabTestOrderCreateSerializer(serializers.ModelSerializer):
#     """Serializer for creating lab test orders"""
    
#     class Meta:
#         model = LabTestOrder
#         fields = [
#             'consultation', 'medical_record', 'patient_profile',
#             'test_catalog', 'priority', 'collection_instructions',
#             'collection_location', 'clinical_notes', 'clinical_indication',
#         ]
    
#     def create(self, validated_data):
#         # Set doctor_profile from request user
#         request = self.context.get('request')
#         if request and hasattr(request.user, 'profile'):
#             if hasattr(request.user.profile, 'doctor_profile'):
#                 validated_data['doctor_profile'] = request.user.profile.doctor_profile
        
#         # Set default status
#         validated_data['status'] = 'ordered'
        
#         return super().create(validated_data)


class LabPanelSerializer(serializers.ModelSerializer):
    """Serializer for the LabPanel model"""
    
    tests_count = serializers.IntegerField(source='tests.count', read_only=True)
    tests_list = LabTestCatalogListSerializer(source='tests', many=True, read_only=True)
    
    class Meta:
        model = LabPanel
        fields = [
            'id', 'name', 'code', 'description', 'tests', 'tests_count',
            'tests_list', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class LabTestProfileSerializer(serializers.ModelSerializer):
    """Serializer for the LabTestProfile model"""
    
    patient_name = serializers.SerializerMethodField()
    test_name = serializers.CharField(source='test.name', read_only=True)
    test_code = serializers.CharField(source='test.code', read_only=True)
    trend_display = serializers.CharField(source='get_trend_display', read_only=True)
    
    class Meta:
        model = LabTestProfile
        fields = [
            'id', 'patient_profile', 'patient_name', 'test', 'test_name',
            'test_code', 'last_value', 'last_value_date', 'trend',
            'trend_display', 'baseline_value', 'baseline_date',
            'alert_threshold_high', 'alert_threshold_low',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()


class LabOrderTemplateSerializer(serializers.ModelSerializer):
    """Serializer for the LabOrderTemplate model"""
    
    created_by_name = serializers.SerializerMethodField()
    tests_count = serializers.IntegerField(source='tests.count', read_only=True)
    tests_list = LabTestCatalogListSerializer(source='tests', many=True, read_only=True)
    
    class Meta:
        model = LabOrderTemplate
        fields = [
            'id', 'name', 'description', 'tests', 'tests_count', 'tests_list',
            'created_by', 'created_by_name', 'is_public', 'usage_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'usage_count', 'created_at', 'updated_at')
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"Dr. {obj.created_by.profile.user.get_full_name()}"
        return None



class LabResultVerifySerializer(serializers.Serializer):
    """Serializer for verifying lab results"""
    
    result_id = serializers.IntegerField(required=True)
    verified = serializers.BooleanField(required=True)
    comments = serializers.CharField(required=False, allow_blank=True)


class LabOrderCancelSerializer(serializers.Serializer):
    """Serializer for cancelling lab orders"""
    
    reason = serializers.CharField(required=True)
    
    # apps/labs/serializers.py
from rest_framework import serializers
from .models import LabTestOrder
from accounts.models import Profile, PatientProfile


class LabTestOrderSerializer(serializers.ModelSerializer):
    """Read serializer"""
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    mh_user_id = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = LabTestOrder
        fields = [
            'id', 'order_number',
            'mh_user_id', 'patient_name', 'doctor_name',
            'test_name', 'priority', 'priority_display',
            'clinical_notes', 'clinical_indication',
            'status', 'status_display', 'is_active',
            'ordered_date', 'collected_date', 'completed_date', 'cancelled_date',
            'result_value', 'result_notes', 'is_abnormal',
            'created_at', 'updated_at',
        ]

    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"

    def get_mh_user_id(self, obj):
        return obj.patient_profile.profile.mh_user_id


class LabTestOrderCreateSerializer(serializers.Serializer):
    """Write serializer — accepts `mh_user_id`"""
    mh_user_id = serializers.CharField(required=True)
    test_name = serializers.CharField()
    priority = serializers.ChoiceField(
        choices=LabTestOrder.PRIORITY_CHOICES, required=False, default='routine'
    )
    clinical_notes = serializers.CharField(required=False, allow_blank=True)
    clinical_indication = serializers.CharField(required=False, allow_blank=True)

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

        # 2. Resolve doctor
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile:
            raise serializers.ValidationError(
                {"detail": "Only doctors can order lab tests."}
            )

        # 3. Create the order
        return LabTestOrder.objects.create(
            patient_profile=patient_profile,
            doctor_profile=doctor_profile,
            status='ordered',
            **validated_data,
        )