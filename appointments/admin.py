# apps/appointments/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import Clinic, Appointment, QueueEntry, DoctorAvailability


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    """Admin configuration for Clinic model"""
    
    list_display = ['id', 'name', 'phone', 'email', 'is_active', 'doctor_count', 'created_at']
    list_filter = ['is_active', 'allow_online_booking', 'requires_doctor_selection']
    search_fields = ['name', 'address', 'phone', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def doctor_count(self, obj):
        return obj.doctors.count()
    doctor_count.short_description = 'Number of Doctors'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'phone', 'email')
        }),
        ('Doctor Management', {
            'fields': ('doctors',)
        }),
        ('Settings', {
            'fields': ('is_active', 'appointment_duration', 'allow_online_booking', 'requires_doctor_selection')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Admin configuration for Appointment model"""
    
    list_display = [
        'id', 'patient_profile', 'doctor_profile', 'clinic', 
        'appointment_date', 'start_time', 'end_time', 
        'status', 'type', 'is_doctor_assigned', 'created_at'
    ]
    list_filter = ['status', 'type', 'appointment_date', 'clinic']
    search_fields = [
        'patient_profile__profile__user__email',
        'patient_profile__profile__user__first_name',
        'patient_profile__profile__user__last_name',
        'doctor_profile__profile__user__first_name',
        'doctor_profile__profile__user__last_name',
        'reason'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 
        'doctor_assigned_at', 'doctor_assigned_by'
    ]
    
    def is_doctor_assigned(self, obj):
        return obj.doctor_profile is not None
    is_doctor_assigned.boolean = True
    is_doctor_assigned.short_description = 'Doctor Assigned'
    
    fieldsets = (
        ('Patient & Doctor', {
            'fields': ('patient_profile', 'doctor_profile', 'clinic')
        }),
        ('Appointment Details', {
            'fields': ('appointment_date', 'start_time', 'end_time', 'type', 'status')
        }),
        ('Additional Information', {
            'fields': ('reason', 'notes')
        }),
        ('Assignment Info', {
            'fields': ('doctor_assigned_at', 'doctor_assigned_by'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirm_appointments', 'cancel_appointments', 'complete_appointments']
    
    def confirm_appointments(self, request, queryset):
        """Confirm selected appointments"""
        updated = queryset.filter(status='scheduled').update(status='confirmed')
        self.message_user(request, f'{updated} appointments confirmed.')
    confirm_appointments.short_description = 'Confirm selected appointments'
    
    def cancel_appointments(self, request, queryset):
        """Cancel selected appointments"""
        updated = queryset.filter(status__in=['scheduled', 'confirmed']).update(status='cancelled')
        self.message_user(request, f'{updated} appointments cancelled.')
    cancel_appointments.short_description = 'Cancel selected appointments'
    
    def complete_appointments(self, request, queryset):
        """Complete selected appointments"""
        updated = queryset.filter(status__in=['confirmed', 'in_progress']).update(status='completed')
        self.message_user(request, f'{updated} appointments completed.')
    complete_appointments.short_description = 'Complete selected appointments'


@admin.register(QueueEntry)
class QueueEntryAdmin(admin.ModelAdmin):
    """Admin configuration for QueueEntry model"""
    
    list_display = [
        'id', 'patient_profile', 'doctor_profile', 'queue_position',
        'status', 'urgency_level', 'priority', 'wait_time_minutes', 'created_at'
    ]
    list_filter = ['status', 'urgency_level', 'created_at']
    search_fields = [
        'patient_profile__profile__user__email',
        'patient_profile__profile__user__first_name',
        'patient_profile__profile__user__last_name',
        'doctor_profile__profile__user__first_name',
        'doctor_profile__profile__user__last_name',
        'reason'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at', 'admitted_at']
    
    fieldsets = (
        ('Patient & Doctor', {
            'fields': ('patient_profile', 'doctor_profile')
        }),
        ('Queue Details', {
            'fields': ('queue_position', 'status', 'urgency_level', 'priority')
        }),
        ('Additional Information', {
            'fields': ('reason', 'wait_time_minutes', 'admitted_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['admit_patients', 'cancel_queue_entries']
    
    def admit_patients(self, request, queryset):
        """Admit selected patients from queue"""
        updated = queryset.filter(status='waiting').update(status='admitted', admitted_at=timezone.now())
        self.message_user(request, f'{updated} patients admitted.')
    admit_patients.short_description = 'Admit selected patients'
    
    def cancel_queue_entries(self, request, queryset):
        """Cancel selected queue entries"""
        updated = queryset.filter(status='waiting').update(status='cancelled')
        self.message_user(request, f'{updated} queue entries cancelled.')
    cancel_queue_entries.short_description = 'Cancel selected queue entries'


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    """Admin configuration for DoctorAvailability model"""
    
    list_display = [
        'id', 'doctor_profile', 'get_day_display', 'start_time', 
        'end_time', 'is_available', 'created_at'
    ]  # ✅ Removed 'specific_date' from list_display
    list_filter = ['day_of_week', 'is_available']  # ✅ Removed 'specific_date' from list_filter
    search_fields = [
        'doctor_profile__profile__user__first_name',
        'doctor_profile__profile__user__last_name',
        'doctor_profile__profile__user__email'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Day'
    get_day_display.admin_order_field = 'day_of_week'
    
    fieldsets = (
        ('Doctor', {
            'fields': ('doctor_profile',)
        }),
        ('Availability', {
            'fields': ('day_of_week', 'start_time', 'end_time', 'is_available')
        }),
        # ✅ Removed the 'specific_date' and 'break' fieldsets since they might not exist
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )