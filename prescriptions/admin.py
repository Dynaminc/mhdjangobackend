# apps/prescriptions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    MedicationCatalog, Prescription, 
    MedicationInteraction, MedicationSchedule, MedicationAdherence
)


# ============================================
# MedicationCatalog Admin
# ============================================
@admin.register(MedicationCatalog)
class MedicationCatalogAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'brand_name',
        'category',
        'form',
        'is_active',
        'is_controlled'
    )
    list_filter = ('category', 'form', 'is_active', 'is_controlled', 'schedule')
    search_fields = ('code', 'name', 'brand_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'brand_name', 'category', 'description')
        }),
        ('Form & Administration', {
            'fields': ('form', 'route_of_administration')
        }),
        ('Dosage', {
            'fields': ('default_dosage', 'dosage_unit', 'dosage_form', 'strength', 'concentration')
        }),
        ('Regulatory', {
            'fields': ('schedule', 'is_controlled', 'requires_prescription')
        }),
        ('Safety', {
            'fields': ('contraindications', 'warnings', 'side_effects', 'interactions', 'pregnancy_category', 'breastfeeding_safety'),
            'classes': ('collapse',)
        }),
        ('Cost', {
            'fields': ('average_cost',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'requires_monitoring', 'monitoring_tests'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# apps/prescriptions/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import Prescription


# apps/prescriptions/admin.py
from django.contrib import admin
from .models import Prescription


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'get_patient',
        'get_doctor',
        'consultation',
        'quantity',
        'created_at',
    )
    list_filter = ('created_at',)
    search_fields = (
        'name',
        'instructions',
        'patient_profile__profile__user__first_name',
        'patient_profile__profile__user__last_name',
        'patient_profile__profile__user__email',
        'patient_profile__profile__mh_user_id',
        'doctor_profile__profile__user__first_name',
        'doctor_profile__profile__user__last_name',
    )
    raw_id_fields = ('patient_profile', 'doctor_profile', 'consultation')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 25

    fieldsets = (
        ('Relationships', {
            'fields': ('id', 'patient_profile', 'doctor_profile', 'consultation')
        }),
        ('Item', {
            'fields': ('name', 'instructions', 'quantity')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
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

    @admin.display(description='Doctor',
                   ordering='doctor_profile__profile__user__first_name')
    def get_doctor(self, obj):
        if not obj.doctor_profile_id:
            return '—'
        user = obj.doctor_profile.profile.user
        return f"Dr. {user.get_full_name() or user.email}"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient_profile__profile__user',
            'doctor_profile__profile__user',
            'consultation',
        )
        
        
# ============================================
# RefillRequest Admin
# # ============================================
# @admin.register(RefillRequest)
# class RefillRequestAdmin(admin.ModelAdmin):
#     list_display = (
#         'get_patient',
#         'prescription',
#         'status',
#         'requested_date',
#         'reviewed_date'
#     )
#     list_filter = ('status', 'requested_date')
#     search_fields = (
#         'patient_profile__profile__user__username',
#         'patient_profile__profile__user__email',
#         'prescription__prescription_number'
#     )
#     raw_id_fields = ('patient_profile', 'prescription', 'reviewed_by')
#     readonly_fields = ('requested_date', 'created_at', 'updated_at')
#     ordering = ('-requested_date',)
    
#     fieldsets = (
#         ('Request Details', {
#             'fields': ('prescription', 'patient_profile', 'status', 'reason', 'notes')
#         }),
#         ('Review', {
#             'fields': ('reviewed_by', 'reviewed_date', 'review_notes')
#         }),
#         ('Timestamps', {
#             'fields': ('requested_date', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     def get_patient(self, obj):
#         return obj.patient_profile.profile.user.get_full_name()
#     get_patient.short_description = 'Patient'
    
#     actions = ['approve_requests', 'reject_requests']
    
#     def approve_requests(self, request, queryset):
#         updated = 0
#         for refill in queryset:
#             if refill.status == 'pending':
#                 refill.approve(request.user.profile.doctor_profile)
#                 updated += 1
#         self.message_user(request, f'{updated} refill requests approved.')
#     approve_requests.short_description = 'Approve selected refill requests'
    
#     def reject_requests(self, request, queryset):
#         updated = 0
#         for refill in queryset:
#             if refill.status == 'pending':
#                 refill.reject(request.user.profile.doctor_profile)
#                 updated += 1
#         self.message_user(request, f'{updated} refill requests rejected.')
#     reject_requests.short_description = 'Reject selected refill requests'


# ============================================
# MedicationInteraction Admin
# ============================================
@admin.register(MedicationInteraction)
class MedicationInteractionAdmin(admin.ModelAdmin):
    list_display = (
        'medication_a',
        'medication_b',
        'severity',
        'description_preview'
    )
    list_filter = ('severity',)
    search_fields = ('medication_a__name', 'medication_b__name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Medications', {
            'fields': ('medication_a', 'medication_b')
        }),
        ('Interaction Details', {
            'fields': ('severity', 'description', 'mechanism', 'management')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def description_preview(self, obj):
        return obj.description[:100] + ('...' if len(obj.description) > 100 else '')
    description_preview.short_description = 'Description'


# ============================================
# MedicationSchedule Admin
# ============================================
@admin.register(MedicationSchedule)
class MedicationScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'prescription',
        'day_of_week',
        'time',
        'notes_preview'
    )
    list_filter = ('day_of_week',)
    search_fields = ('prescription__prescription_number',)
    raw_id_fields = ('prescription',)
    readonly_fields = ('created_at', 'updated_at')
    
    def notes_preview(self, obj):
        return obj.notes[:50] + ('...' if len(obj.notes) > 50 else '')
    notes_preview.short_description = 'Notes'


# ============================================
# MedicationAdherence Admin
# ============================================
@admin.register(MedicationAdherence)
class MedicationAdherenceAdmin(admin.ModelAdmin):
    list_display = (
        'get_patient',
        'prescription',
        'date',
        'taken_badge',
        'time_taken'
    )
    list_filter = ('taken', 'date')
    search_fields = (
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'prescription__prescription_number'
    )
    raw_id_fields = ('patient_profile', 'prescription')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-date',)
    
    fieldsets = (
        ('Adherence Record', {
            'fields': ('prescription', 'patient_profile', 'date', 'taken', 'time_taken')
        }),
        ('Notes', {
            'fields': ('skipped_reason', 'side_effects', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_patient(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    get_patient.short_description = 'Patient'
    
    def taken_badge(self, obj):
        if obj.taken:
            return format_html('<span style="color: #22c55e;">✅ Taken</span>')
        return format_html('<span style="color: #ef4444;">❌ Missed</span>')
    taken_badge.short_description = 'Status'