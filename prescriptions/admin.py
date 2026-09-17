# apps/prescriptions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    MedicationCatalog, Prescription, RefillRequest,
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


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Admin for the simplified Prescription model"""

    # -------------------------------------------------
    # List view
    # -------------------------------------------------
    list_display = [
        'prescription_number',
        'patient_name',
        'doctor_name',
        'medication_name',
        'dosage',
        'frequency',
        'status',
        'prescribed_date',
        'expiry_date',
    ]

    list_filter = [
        'status',
        'frequency',
        'duration_unit',
        'prescribed_date',
    ]

    search_fields = [
        'prescription_number',
        'medication_name',
        'dosage',
        'patient_profile__profile__user__first_name',
        'patient_profile__profile__user__last_name',
        'patient_profile__profile__user__email',
        'patient_profile__profile__mh_user_id',
        'doctor_profile__profile__user__first_name',
        'doctor_profile__profile__user__last_name',
    ]

    readonly_fields = [
        'prescription_number',
        'refills_used',
        'prescribed_date',
        'expiry_date',
        'last_filled_date',
        'created_at',
        'updated_at',
    ]

    ordering = ['-prescribed_date']
    date_hierarchy = 'prescribed_date'
    list_per_page = 25

    # -------------------------------------------------
    # Detail form layout
    # -------------------------------------------------
    fieldsets = (
        ('Identifiers', {
            'fields': (
                'prescription_number',
                'patient_profile',
                'doctor_profile',
            )
        }),
        ('Medication', {
            'fields': (
                'medication_name',
                'dosage',
                'frequency',
                'frequency_custom',
            )
        }),
        ('Duration & Quantity', {
            'fields': (
                'duration_value',
                'duration_unit',
                'quantity',
                'refills',
                'refills_used',
            )
        }),
        ('Instructions', {
            'fields': (
                'instructions',
                'additional_notes',
            )
        }),
        ('Dates', {
            'fields': (
                'prescribed_date',
                'start_date',
                'expiry_date',
                'last_filled_date',
            )
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Pharmacy', {
            'fields': (
                'pharmacy_name',
                'pharmacy_phone',
                'pharmacy_address',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # -------------------------------------------------
    # Custom columns
    # -------------------------------------------------
    @admin.display(description='Patient', ordering='patient_profile__profile__user__first_name')
    def patient_name(self, obj):
        try:
            return obj.patient_profile.profile.user.get_full_name()
        except Exception:
            return '-'

    @admin.display(description='Doctor', ordering='doctor_profile__profile__user__first_name')
    def doctor_name(self, obj):
        try:
            return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
        except Exception:
            return '-'

    # -------------------------------------------------
    # Bulk actions
    # -------------------------------------------------
    actions = ['mark_active', 'mark_completed', 'mark_cancelled', 'mark_expired']

    @admin.action(description='Mark selected prescriptions as Active')
    def mark_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} prescriptions marked as Active.')

    @admin.action(description='Mark selected prescriptions as Completed')
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} prescriptions marked as Completed.')

    @admin.action(description='Mark selected prescriptions as Cancelled')
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} prescriptions marked as Cancelled.')

    @admin.action(description='Mark selected prescriptions as Expired')
    def mark_expired(self, request, queryset):
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} prescriptions marked as Expired.')

    # -------------------------------------------------
    # Permissions — only doctors/staff can add or change
    # -------------------------------------------------
    def has_add_permission(self, request):
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
# ============================================
# RefillRequest Admin
# ============================================
@admin.register(RefillRequest)
class RefillRequestAdmin(admin.ModelAdmin):
    list_display = (
        'get_patient',
        'prescription',
        'status',
        'requested_date',
        'reviewed_date'
    )
    list_filter = ('status', 'requested_date')
    search_fields = (
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'prescription__prescription_number'
    )
    raw_id_fields = ('patient_profile', 'prescription', 'reviewed_by')
    readonly_fields = ('requested_date', 'created_at', 'updated_at')
    ordering = ('-requested_date',)
    
    fieldsets = (
        ('Request Details', {
            'fields': ('prescription', 'patient_profile', 'status', 'reason', 'notes')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_date', 'review_notes')
        }),
        ('Timestamps', {
            'fields': ('requested_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_patient(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    get_patient.short_description = 'Patient'
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        updated = 0
        for refill in queryset:
            if refill.status == 'pending':
                refill.approve(request.user.profile.doctor_profile)
                updated += 1
        self.message_user(request, f'{updated} refill requests approved.')
    approve_requests.short_description = 'Approve selected refill requests'
    
    def reject_requests(self, request, queryset):
        updated = 0
        for refill in queryset:
            if refill.status == 'pending':
                refill.reject(request.user.profile.doctor_profile)
                updated += 1
        self.message_user(request, f'{updated} refill requests rejected.')
    reject_requests.short_description = 'Reject selected refill requests'


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