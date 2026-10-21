from django.contrib import admin
from .models import LabTestOrder


@admin.register(LabTestOrder)
class LabTestOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'test_name', 'get_patient', 'get_doctor',
        'consultation', 'has_result', 'created_at',
    )
    list_filter = ('created_at',)
    search_fields = (
        'test_name', 'instructions', 'clinical_indication',
        'patient_profile__profile__user__first_name',
        'patient_profile__profile__user__last_name',
        'patient_profile__profile__mh_user_id',
    )
    raw_id_fields = ('patient_profile', 'doctor_profile', 'consultation')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Relationships', {
            'fields': ('id', 'patient_profile', 'doctor_profile', 'consultation')
        }),
        ('Order', {
            'fields': ('test_name', 'instructions', 'clinical_indication')
        }),
        ('Result', {
            'fields': ('result_value', 'attachment_urls', 'doctor_comment')   # ✅ add
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Patient')
    def get_patient(self, obj):
        if not obj.patient_profile_id:
            return '—'
        user = obj.patient_profile.profile.user
        return user.get_full_name() or user.email

    @admin.display(description='Doctor')
    def get_doctor(self, obj):
        if not obj.doctor_profile_id:
            return '—'
        user = obj.doctor_profile.profile.user
        return f"Dr. {user.get_full_name() or user.email}"

    @admin.display(description='Has Result', boolean=True)
    def has_result(self, obj):
        return bool(obj.result_value or obj.attachment_urls)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient_profile__profile__user',
            'doctor_profile__profile__user',
            'consultation',
        )