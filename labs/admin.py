# apps/labs/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    LabTestCatalog, LabTestOrder, LabTestResult,
    LabTestAttachment, LabPanel, LabTestProfile,
    LabOrderTemplate
)


# ============================================
# LabTestCatalog Admin
# ============================================
@admin.register(LabTestCatalog)
class LabTestCatalogAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'short_name',
        'category',
        'sample_type',
        'cost',
        'is_active'
    )
    list_filter = ('category', 'sample_type', 'is_active', 'fasting_required')
    search_fields = ('code', 'name', 'short_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'short_name', 'category', 'description')
        }),
        ('Sample Requirements', {
            'fields': ('sample_type', 'sample_volume', 'sample_container', 'fasting_required', 'fasting_hours')
        }),
        ('Reference Ranges', {
            'fields': ('reference_range_male', 'reference_range_female', 'reference_range_child', 'unit')
        }),
        ('Cost & Turnaround', {
            'fields': ('cost', 'turnaround_time_hours')
        }),
        ('Clinical Information', {
            'fields': ('clinical_indications', 'interpretation_notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'requires_authorization', 'requires_consent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================
# LabTestOrder Admin
# ============================================
# apps/labs/admin.py
from django.contrib import admin
from .models import LabTestOrder


@admin.register(LabTestOrder)
class LabTestOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'patient_name', 'doctor_name',
        'test_name', 'priority', 'status', 'ordered_date',
    ]
    list_filter = ['status', 'priority', 'ordered_date']
    search_fields = [
        'order_number', 'test_name',
        'patient_profile__profile__user__first_name',
        'patient_profile__profile__user__last_name',
        'patient_profile__profile__mh_user_id',
        'doctor_profile__profile__user__first_name',
        'doctor_profile__profile__user__last_name',
    ]
    readonly_fields = [
        'order_number', 'ordered_date', 'collected_date',
        'completed_date', 'cancelled_date',
        'created_at', 'updated_at',
    ]
    ordering = ['-ordered_date']
    date_hierarchy = 'ordered_date'

    fieldsets = (
        ('Identifiers', {
            'fields': ('order_number', 'patient_profile', 'doctor_profile')
        }),
        ('Test', {
            'fields': ('test_name', 'priority', 'clinical_notes', 'clinical_indication')
        }),
        ('Status', {
            'fields': ('status', 'ordered_date', 'collected_date',
                       'completed_date', 'cancelled_date')
        }),
        ('Results', {
            'fields': ('result_value', 'result_notes', 'is_abnormal')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Patient')
    def patient_name(self, obj):
        try:
            return obj.patient_profile.profile.user.get_full_name()
        except Exception:
            return '-'

    @admin.display(description='Doctor')
    def doctor_name(self, obj):
        try:
            return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
        except Exception:
            return '-'

    actions = ['mark_completed', 'mark_cancelled']

    @admin.action(description='Mark selected as Completed')
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} lab orders marked Completed.')

    @admin.action(description='Mark selected as Cancelled')
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} lab orders marked Cancelled.')

# ============================================
# LabTestResult Admin
# ============================================
@admin.register(LabTestResult)
class LabTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'result_value',
        'unit',
        'is_abnormal_badge',
        'is_critical_badge',
        'status',
        'verified_at'
    )
    list_filter = ('is_abnormal', 'is_critical', 'status', 'created_at')
    search_fields = ('order__order_number', 'result_value')
    raw_id_fields = ('order', 'verified_by', 'reviewed_by')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Order', {
            'fields': ('order',)
        }),
        ('Result', {
            'fields': ('result_value', 'result_numeric', 'unit', 'reference_range', 'result_text')
        }),
        ('Flags', {
            'fields': ('is_abnormal', 'is_critical', 'is_high', 'is_low')
        }),
        ('Interpretation', {
            'fields': ('interpretation',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_at', 'status')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'comments'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_abnormal_badge(self, obj):
        if obj.is_abnormal:
            return format_html('<span style="color: #ef4444;">⚠️ Abnormal</span>')
        return format_html('<span style="color: #22c55e;">✅ Normal</span>')
    is_abnormal_badge.short_description = 'Result'
    
    def is_critical_badge(self, obj):
        if obj.is_critical:
            return format_html('<span style="color: #dc2626; font-weight: bold;">🚨 CRITICAL</span>')
        return '-'
    is_critical_badge.short_description = 'Critical'
    
    actions = ['verify_results', 'mark_normal', 'mark_abnormal']
    
    def verify_results(self, request, queryset):
        from django.utils import timezone
        doctor = request.user.profile.doctor_profile
        updated = 0
        for result in queryset:
            if not result.is_verified:
                result.verify(doctor)
                updated += 1
        self.message_user(request, f'{updated} results verified.')
    verify_results.short_description = 'Verify selected results'
    
    def mark_normal(self, request, queryset):
        updated = 0
        for result in queryset:
            if result.is_abnormal:
                result.mark_normal()
                updated += 1
        self.message_user(request, f'{updated} results marked as normal.')
    mark_normal.short_description = 'Mark selected as Normal'
    
    def mark_abnormal(self, request, queryset):
        updated = 0
        for result in queryset:
            if not result.is_abnormal:
                result.mark_abnormal()
                updated += 1
        self.message_user(request, f'{updated} results marked as abnormal.')
    mark_abnormal.short_description = 'Mark selected as Abnormal'


# ============================================
# LabTestAttachment Admin
# ============================================
@admin.register(LabTestAttachment)
class LabTestAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        'file_name',
        'result',
        'file_size_display',
        'uploaded_by',
        'created_at'
    )
    search_fields = ('file_name', 'description')
    raw_id_fields = ('result', 'uploaded_by')
    readonly_fields = ('file_size', 'created_at', 'updated_at')
    
    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'Size'


# ============================================
# LabPanel Admin
# ============================================
@admin.register(LabPanel)
class LabPanelAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'test_count')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    filter_horizontal = ('tests',)
    readonly_fields = ('created_at', 'updated_at')
    
    def test_count(self, obj):
        return obj.tests.count()
    test_count.short_description = 'Tests'


# ============================================
# LabTestProfile Admin
# ============================================
@admin.register(LabTestProfile)
class LabTestProfileAdmin(admin.ModelAdmin):
    list_display = (
        'get_patient',
        'test',
        'last_value',
        'last_value_date',
        'trend'
    )
    list_filter = ('trend',)
    search_fields = (
        'patient_profile__profile__user__username',
        'patient_profile__profile__user__email',
        'test__name'
    )
    raw_id_fields = ('patient_profile', 'test')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_patient(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    get_patient.short_description = 'Patient'


# ============================================
# LabOrderTemplate Admin
# ============================================
@admin.register(LabOrderTemplate)
class LabOrderTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_public', 'created_by', 'usage_count')
    list_filter = ('is_public',)
    search_fields = ('name', 'description')
    filter_horizontal = ('tests',)
    raw_id_fields = ('created_by',)
    readonly_fields = ('usage_count', 'created_at', 'updated_at')