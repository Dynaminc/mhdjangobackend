# apps/labs/serializers.py
from rest_framework import serializers

from .models import LabTestOrder
from accounts.models import Profile, PatientProfile
from consultations.models import Consultation


class LabTestOrderSerializer(serializers.ModelSerializer):
    mh_user_id = serializers.CharField(
        source='patient_profile.profile.mh_user_id', read_only=True
    )
    patient_name = serializers.CharField(
        source='patient_profile.profile.user.get_full_name', read_only=True
    )
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = LabTestOrder
        fields = [
            'id', 'consultation', 'mh_user_id', 'patient_name', 'doctor_name',
            'test_name', 'instructions', 'clinical_indication',
            'result_value', 'attachment_urls',
            'doctor_comment',                      # ✅ add
            'created_at',
        ]

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
    
class LabTestOrderCreateSerializer(serializers.Serializer):
    """Create one lab test item using mh_user_id + consultation_id."""
    mh_user_id = serializers.CharField(required=True)
    consultation_id = serializers.IntegerField(required=False, allow_null=True)

    test_name = serializers.CharField()
    instructions = serializers.CharField(required=False, allow_blank=True)
    clinical_indication = serializers.CharField(required=False, allow_blank=True)

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
                {"detail": "Only doctors can order lab tests."}
            )

        # 3. Consultation (optional, must match patient)
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

        return LabTestOrder.objects.create(
            consultation=consultation,
            patient_profile=patient_profile,
            doctor_profile=doctor_profile,
            **validated_data,
        )