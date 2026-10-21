# apps/consultations/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Consultation, Examination, PastMedicalHistory, MedicalRecord


def badge(text, color='#22c55e'):
    return mark_safe(f'<span style="color:{color};font-weight:600;">{text}</span>')


# ============================================
# Consultation Admin
# ============================================
@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_patient',
        'get_doctor',
        'type',
        'status',
        'appointment',
        'get_chat_status',
        'created_at',
    )
    list_filter = ('status', 'type', 'created_at')
    search_fields = (
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'patient_profile__profile__user__first_name',
        'patient_profile__profile__user__last_name',
        'patient_profile__profile__mh_user_id',
        'doctor_profile__profile__user__username',
        'doctor_profile__profile__user__email',
    )
    raw_id_fields = ('patient_profile', 'doctor_profile', 'appointment')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 25
    save_on_top = True

    fieldsets = (
        ('Identifiers', {
            'fields': ('id', 'appointment', 'patient_profile', 'doctor_profile')
        }),
        ('Clinical Data', {
            'fields': ('hpc', 'symptoms', 'duration', 'vitals', 'examinations')
        }),
        ('Assessment & Plan', {
            'fields': ('assessment', 'plan')
        }),
        ('Metadata', {
            'fields': ('type', 'status', 'clinic_location', 'chat_conversation_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # ── Columns ──────────────────────────────────────────────
    @admin.display(description='Patient',
                   ordering='patient_profile__profile__user__first_name')
    def get_patient(self, obj):
        if not obj.patient_profile_id:
            return '—'
        user = obj.patient_profile.profile.user
        return user.get_full_name() or user.email

    @admin.display(description='Doctor',
                   ordering='doctor_profile__profile__user__first_name')
    def get_doctor(self, obj):
        if not obj.doctor_profile_id:
            return '—'
        user = obj.doctor_profile.profile.user
        return f"Dr. {user.get_full_name() or user.email}"

    @admin.display(description='Chat')
    def get_chat_status(self, obj):
        if obj.chat_conversation_id:
            return badge('💬 Active', '#22c55e')
        return badge('📴 No Chat', '#94a3b8')

    # ── Actions ──────────────────────────────────────────────
    actions = ['complete_consultations', 'cancel_consultations']

    @admin.action(description='Complete selected consultations')
    def complete_consultations(self, request, queryset):
        updated = 0
        for consultation in queryset:
            if consultation.status != 'completed':
                consultation.complete()
                updated += 1
        self.message_user(request, f'{updated} consultations completed.')

    @admin.action(description='Cancel selected consultations')
    def cancel_consultations(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} consultations cancelled.')

    # ── Performance ──────────────────────────────────────────
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient_profile__profile__user',
            'doctor_profile__profile__user',
            'appointment',
        )


# ============================================
# Examination Admin
# ============================================
@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'consultation',
        'examination_type',
        'is_normal',
        'get_findings_preview',
        'get_vitals_preview',
    )
    list_filter = ('examination_type', 'is_normal', 'created_at')
    search_fields = ('consultation__id', 'findings', 'notes')
    raw_id_fields = ('consultation',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Examination Details', {
            'fields': ('id', 'consultation', 'examination_type',
                       'findings', 'is_normal', 'notes')
        }),
        ('Vitals', {
            'fields': ('bp_systolic', 'bp_diastolic', 'heart_rate',
                       'respiratory_rate', 'temperature', 'spo2',
                       'weight', 'height'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Findings')
    def get_findings_preview(self, obj):
        if not obj.findings:
            return '—'
        return obj.findings[:50] + ('...' if len(obj.findings) > 50 else '')

    @admin.display(description='BP')
    def get_vitals_preview(self, obj):
        if obj.bp_systolic and obj.bp_diastolic:
            return f"{obj.bp_systolic}/{obj.bp_diastolic}"
        return '—'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'consultation__patient_profile__profile__user',
            'consultation__doctor_profile__profile__user',
        )


# ============================================
# PastMedicalHistory Admin
# ============================================
@admin.register(PastMedicalHistory)
class PastMedicalHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'get_patient',
        'history_type',
        'content_preview',
        'is_active',
        'recorded_date',
    )
    list_filter = ('history_type', 'is_active', 'recorded_date')
    search_fields = (
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'patient_profile__profile__mh_user_id',
        'content',
    )
    raw_id_fields = ('patient_profile', 'recorded_by')
    readonly_fields = ('id', 'recorded_date', 'created_at', 'updated_at')
    ordering = ('-recorded_date',)

    fieldsets = (
        ('Patient', {'fields': ('id', 'patient_profile')}),
        ('History Details', {
            'fields': ('history_type', 'content', 'is_active', 'notes')
        }),
        ('Recorded By', {
            'fields': ('recorded_by', 'recorded_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Patient',
                   ordering='patient_profile__profile__user__first_name')
    def get_patient(self, obj):
        if not obj.patient_profile_id:
            return '—'
        user = obj.patient_profile.profile.user
        return user.get_full_name() or user.email

    @admin.display(description='Content')
    def content_preview(self, obj):
        if not obj.content:
            return '—'
        return obj.content[:100] + ('...' if len(obj.content) > 100 else '')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient_profile__profile__user',
            'recorded_by__profile__user',
        )


# ============================================
# MedicalRecord Admin
# ============================================
@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = (
        'record_number',
        'get_patient',
        'is_complete',
        'last_review_date',
        'get_active_problems_count',
    )
    list_filter = ('is_complete', 'created_at')
    search_fields = (
        'record_number',
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'patient_profile__profile__mh_user_id',
    )
    raw_id_fields = ('patient_profile', 'last_updated_by')
    readonly_fields = ('id', 'record_number', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Record Information', {
            'fields': ('id', 'record_number', 'patient_profile', 'is_complete')
        }),
        ('Summary', {
            'fields': ('active_problems', 'active_medications_summary', 'allergies_summary')
        }),
        ('Review', {
            'fields': ('last_review_date', 'last_updated_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Patient',
                   ordering='patient_profile__profile__user__first_name')
    def get_patient(self, obj):
        if not obj.patient_profile_id:
            return '—'
        user = obj.patient_profile.profile.user
        return user.get_full_name() or user.email

    @admin.display(description='Problems')
    def get_active_problems_count(self, obj):
        if not obj.active_problems:
            return 0
        return len([line for line in obj.active_problems.split('\n') if line.strip()])

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient_profile__profile__user',
            'last_updated_by__profile__user',
        )