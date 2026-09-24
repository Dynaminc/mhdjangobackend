# apps/specialists/serializers.py
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import (
    Specialist,
    SpecialistTimeline,
    SpecialistCredential,
    SpecialistLanguage,
    SpecialistSocialLink,
    SpecialistTag,
    SpecialistWeeklyAvailability,
    SpecialistReview,
    SpecialistReferral,
)


# =====================================================
# NESTED SERIALIZERS
# =====================================================
class SpecialistTimelineSerializer(serializers.ModelSerializer):
    year_range = serializers.CharField(read_only=True)

    class Meta:
        model = SpecialistTimeline
        fields = [
            'id', 'start_year', 'end_year', 'is_current',
            'title', 'organization', 'location', 'description',
            'display_order', 'year_range',
        ]
        read_only_fields = ['id', 'year_range']


class SpecialistCredentialSerializer(serializers.ModelSerializer):
    credential_type_display = serializers.CharField(
        source='get_credential_type_display', read_only=True
    )

    class Meta:
        model = SpecialistCredential
        fields = [
            'id', 'credential_type', 'credential_type_display',
            'title', 'institution', 'year_obtained', 'country',
            'verification_url', 'is_verified', 'display_order',
        ]
        read_only_fields = ['id', 'is_verified']


class SpecialistLanguageSerializer(serializers.ModelSerializer):
    proficiency_display = serializers.CharField(
        source='get_proficiency_display', read_only=True
    )

    class Meta:
        model = SpecialistLanguage
        fields = ['id', 'language', 'proficiency', 'proficiency_display', 'display_order']
        read_only_fields = ['id']


class SpecialistSocialLinkSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(
        source='get_platform_display', read_only=True
    )

    class Meta:
        model = SpecialistSocialLink
        fields = ['id', 'platform', 'platform_display', 'url', 'label', 'is_public', 'display_order']
        read_only_fields = ['id']


class SpecialistTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialistTag
        fields = ['id', 'name', 'color', 'category', 'display_order']
        read_only_fields = ['id']


class SpecialistWeeklyAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialistWeeklyAvailability
        fields = ['id', 'date', 'is_available', 'slots_count', 'note']
        read_only_fields = ['id']


class SpecialistReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialistReview
        fields = [
            'id', 'rating', 'title', 'body',
            'reviewer_display_name', 'is_anonymous', 'is_published', 'created_at',
        ]
        read_only_fields = ['id', 'is_published', 'created_at']


# =====================================================
# SPECIALIST — LIST (lightweight, for directory cards)
# =====================================================
class SpecialistListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    avatar_display = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    is_available_now = serializers.BooleanField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verification_level_display = serializers.CharField(
        source='get_verification_level_display', read_only=True
    )

    class Meta:
        model = Specialist
        fields = [
            'id', 'slug',
            'title', 'first_name', 'last_name', 'middle_name',
            'full_name', 'display_name', 'initials',
            'credentials', 'specialty', 'specialty_display',
            'sub_specialties', 'headline', 'short_bio',
            'avatar_display',
            'country', 'state', 'city', 'is_remote',
            'years_experience', 'total_consultations',
            'languages',
            'average_rating', 'total_reviews',
            'response_rate_percent', 'recommendation_rate',
            'tags', 'areas_of_expertise',
            'status', 'status_display',
            'is_online_now', 'is_available_now',
            'verification_level', 'verification_level_display',
            'is_verified', 'is_featured',
        ]


# =====================================================
# SPECIALIST — DETAIL (full profile page)
# =====================================================
class SpecialistDetailSerializer(serializers.ModelSerializer):
    # Computed fields
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    avatar_display = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    is_available_now = serializers.BooleanField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verification_level_display = serializers.CharField(
        source='get_verification_level_display', read_only=True
    )

    # Nested
    timeline = SpecialistTimelineSerializer(many=True, read_only=True)
    credentials_list = SpecialistCredentialSerializer(many=True, read_only=True)
    languages_list = SpecialistLanguageSerializer(many=True, read_only=True)
    social_links = SpecialistSocialLinkSerializer(many=True, read_only=True)
    tag_list = SpecialistTagSerializer(many=True, read_only=True)
    weekly_availability = SpecialistWeeklyAvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Specialist
        fields = '__all__'
        read_only_fields = [
            'id', 'slug', 'created_at', 'updated_at',
            'joined_at', 'average_rating', 'total_reviews',
        ]


# =====================================================
# SPECIALIST — CREATE / UPDATE
# =====================================================
class SpecialistWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialist
        exclude = [
            'id', 'slug', 'created_at', 'updated_at',
            'average_rating', 'total_reviews', 'last_active_at',
        ]

    def validate_consultation_formats(self, value):
        valid = [c[0] for c in [
            ('video', 'Video Call'),
            ('in_person', 'In-Person'),
            ('phone', 'Phone Call'),
            ('chat', 'Chat'),
            ('hybrid', 'Hybrid'),
        ]]
        for v in value or []:
            if v not in valid:
                raise serializers.ValidationError(f"'{v}' is not a valid format.")
        return value


# =====================================================
# REFERRAL
# =====================================================
class SpecialistReferralSerializer(serializers.ModelSerializer):
    """Read serializer — safe for patients to view their own referral."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    sex_display = serializers.CharField(source='get_sex_display', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    marital_status_display = serializers.CharField(
        source='get_marital_status_display', read_only=True
    )
    assigned_specialist_details = SpecialistListSerializer(
        source='assigned_specialist', read_only=True
    )

    class Meta:
        model = SpecialistReferral
        fields = [
            'id', 'reference_id',
            # personal
            'first_name', 'last_name', 'age', 'sex', 'sex_display',
            'marital_status', 'marital_status_display',
            'religion', 'tribe',
            # contact
            'country', 'state', 'city', 'phone', 'email',
            # complaint
            'complaint', 'symptoms',
            'duration', 'duration_display',
            'severity', 'severity_display',
            'frequency', 'frequency_display',
            'progression', 'expectations',
            # consent
            'consented_at', 'consent_version',
            # status
            'status', 'status_display',
            # assignment
            'assigned_specialist', 'assigned_specialist_details',
            # review
            'approved_at', 'rejected_at', 'rejection_reason',
            # timestamps
            'submitted_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'reference_id', 'status',
            'consented_at', 'approved_at', 'rejected_at',
            'rejection_reason', 'assigned_specialist',
            'submitted_at', 'created_at', 'updated_at',
        ]


class SpecialistReferralCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer — used by patients to submit a referral.
    Only the fields they should fill are allowed.
    """
    consent = serializers.BooleanField(
        write_only=True,
        help_text="Patient must consent to proceed.",
    )

    class Meta:
        model = SpecialistReferral
        fields = [
            'first_name', 'last_name', 'age', 'sex',
            'marital_status', 'religion', 'tribe',
            'country', 'state', 'city', 'phone', 'email',
            'complaint', 'symptoms', 'duration', 'severity', 'frequency',
            'progression', 'expectations',
            'consent',
        ]

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must consent before submitting a referral."
            )
        return value

    def validate_age(self, value):
        if value < 1 or value > 120:
            raise serializers.ValidationError("Age must be between 1 and 120.")
        return value

    def create(self, validated_data):
        validated_data.pop('consent', None)
        email = validated_data['email'].lower().strip()
        # Reject if the same email submitted in the last 24 hours
        # recent = SpecialistReferral.objects.filter(
        #     email__iexact=email,
        #     submitted_at__gte=timezone.now() - timedelta(hours=24),
        # ).exists()
        # if recent:
        #     raise serializers.ValidationError({
        #         'email': 'A referral from this email was already submitted today. '
        #                 'Please wait 24 hours before submitting another.'
        #     })


        validated_data['consented_at'] = timezone.now()
        validated_data['consent_version'] = 'v1'
        validated_data['status'] = 'pending'
        return super().create(validated_data)


# apps/specialists/serializers.py
class SpecialistReferralStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SpecialistReferral.STATUS_CHOICES)
    assigned_specialist_id = serializers.UUIDField(required=False, allow_null=True)
    review_notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    # ✅ Scheduling info
    meeting_link = serializers.URLField(required=False, allow_blank=True)
    appointment_date = serializers.DateField(required=False, allow_null=True)
    appointment_time = serializers.TimeField(required=False, allow_null=True)

    def validate(self, data):
        s = data.get('status')
        if s == 'rejected' and not data.get('rejection_reason'):
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required."}
            )
        if s == 'scheduled':
            if not data.get('assigned_specialist_id'):
                raise serializers.ValidationError(
                    {"assigned_specialist_id": "Assign a specialist to schedule."}
                )
            if not data.get('appointment_date') or not data.get('appointment_time'):
                raise serializers.ValidationError(
                    {"appointment": "appointment_date and appointment_time are required to schedule."}
                )
        return data