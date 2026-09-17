# apps/consultations/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Consultation, Examination, PastMedicalHistory, MedicalRecord


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
        'created_at'
    )
    list_filter = ('status', 'type', 'created_at')
    search_fields = (
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'doctor_profile__profile__user__username',
        'doctor_profile__profile__user__email'
    )
    raw_id_fields = ('patient_profile', 'doctor_profile', 'appointment')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Relationships', {
            'fields': ('appointment', 'patient_profile', 'doctor_profile')
        }),
        ('Clinical Data', {
            'fields': ('hpc', 'symptoms', 'duration', 'vitals')
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
    
    def get_patient(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    get_patient.short_description = 'Patient'
    get_patient.admin_order_field = 'patient_profile__profile__user__first_name'
    
    def get_doctor(self, obj):
        return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
    get_doctor.short_description = 'Doctor'
    
    def get_chat_status(self, obj):
        if obj.chat_conversation_id:
            return format_html('<span style="color: #22c55e;">💬 Active</span>')
        return format_html('<span style="color: #94a3b8;">📴 No Chat</span>')
    get_chat_status.short_description = 'Chat'
    
    actions = ['complete_consultations', 'cancel_consultations']
    
    def complete_consultations(self, request, queryset):
        updated = 0
        for consultation in queryset:
            if consultation.status != 'completed':
                consultation.complete()
                updated += 1
        self.message_user(request, f'{updated} consultations completed.')
    complete_consultations.short_description = 'Complete selected consultations'
    
    def cancel_consultations(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} consultations cancelled.')
    cancel_consultations.short_description = 'Cancel selected consultations'


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
        'get_vitals_preview'
    )
    list_filter = ('examination_type', 'is_normal', 'created_at')
    search_fields = ('consultation__id', 'findings', 'notes')
    raw_id_fields = ('consultation',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Examination Details', {
            'fields': ('consultation', 'examination_type', 'findings', 'is_normal', 'notes')
        }),
        ('Vitals', {
            'fields': ('bp_systolic', 'bp_diastolic', 'heart_rate', 'respiratory_rate', 'temperature', 'spo2', 'weight', 'height'),
            'classes': ('collapse',)
        }),
        ('Calculated', {
            'fields': ('bmi',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_findings_preview(self, obj):
        return obj.findings[:50] + ('...' if len(obj.findings) > 50 else '')
    get_findings_preview.short_description = 'Findings'
    
    def get_vitals_preview(self, obj):
        if obj.bp_systolic and obj.bp_diastolic:
            return f"{obj.bp_systolic}/{obj.bp_diastolic}"
        return '-'
    get_vitals_preview.short_description = 'BP'


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
        'recorded_date'
    )
    list_filter = ('history_type', 'is_active', 'recorded_date')
    search_fields = (
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'content'
    )
    raw_id_fields = ('patient_profile', 'recorded_by')
    readonly_fields = ('recorded_date', 'created_at', 'updated_at')
    ordering = ('-recorded_date',)
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient_profile',)
        }),
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
    
    def get_patient(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    get_patient.short_description = 'Patient'
    
    def content_preview(self, obj):
        return obj.content[:100] + ('...' if len(obj.content) > 100 else '')
    content_preview.short_description = 'Content'


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
        'get_active_problems_count'
    )
    list_filter = ('is_complete', 'created_at')
    search_fields = (
        'record_number',
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email'
    )
    raw_id_fields = ('patient_profile', 'last_updated_by')
    readonly_fields = ('record_number', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Record Information', {
            'fields': ('record_number', 'patient_profile', 'is_complete')
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
    
    def get_patient(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    get_patient.short_description = 'Patient'
    
    def get_active_problems_count(self, obj):
        if obj.active_problems:
            return len(obj.active_problems.split('\n'))
        return 0
    get_active_problems_count.short_description = 'Problems'