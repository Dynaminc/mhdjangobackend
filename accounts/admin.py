# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Profile, DoctorProfile, PatientProfile


# ============================================
# Profile Inline
# ============================================
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fieldsets = (
        ('Basic Information', {
            'fields': ('role', 'phone', 'age', 'gender', 'date_of_birth')
        }),
        ('Status', {
            'fields': ('is_online', 'login_count', 'last_login_ip', 'last_logout_at'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': ('language', 'timezone', 'notifications_enabled'),
            'classes': ('collapse',)
        }),
        ('Profile Details', {
            'fields': ('profile_picture', 'bio'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('login_count', 'last_login_ip', 'last_logout_at')


# ============================================
# Custom User Admin
# ============================================
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'get_role', 
        'get_profile_type',
        'is_active',
        'is_staff'
    )
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    def get_role(self, obj):
        try:
            return obj.profile.role
        except Profile.DoesNotExist:
            return '-'
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'profile__role'
    
    def get_profile_type(self, obj):
        try:
            if hasattr(obj.profile, 'doctor_profile'):
                return '👨‍⚕️ Doctor'
            elif hasattr(obj.profile, 'patient_profile'):
                return '👤 Patient'
            return '📋 Profile'
        except Profile.DoesNotExist:
            return '-'
    get_profile_type.short_description = 'Profile Type'


# ============================================
# Profile Admin
# ============================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'role',
        'phone',
        'is_online',
        'login_count',
        'get_profile_badge',
        'created_at'
    )
    list_filter = ('role', 'is_online', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('login_count', 'last_login_ip', 'last_logout_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'phone', 'age', 'gender', 'date_of_birth')
        }),
        ('Status', {
            'fields': ('is_online', 'login_count', 'last_login_ip', 'last_logout_at')
        }),
        ('Profile Details', {
            'fields': ('profile_picture', 'bio')
        }),
        ('Preferences', {
            'fields': ('language', 'timezone', 'notifications_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_profile_badge(self, obj):
        if obj.role == 'doctor':
            return '👨‍⚕️ Doctor'
        elif obj.role == 'patient':
            return '👤 Patient'
        return '👤 User'
    get_profile_badge.short_description = 'Type'


# ============================================
# DoctorProfile Admin
# ============================================
@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = (
        'get_doctor_name',
        'get_doctor_email',
        'specialty',
        'license_number',
        'years_experience',
        'rating',
        'is_available',
        'consultation_fee'
    )
    list_filter = ('specialty', 'is_available', 'years_experience')
    search_fields = (
        'profile__user__username',
        'profile__user__email',
        'specialty',
        'license_number'
    )
    raw_id_fields = ('profile',)
    readonly_fields = ('rating', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Profile', {
            'fields': ('profile',)
        }),
        ('Professional Details', {
            'fields': ('specialty', 'license_number', 'years_experience', 'rating', 'consultation_fee')
        }),
        ('Availability', {
            'fields': ('is_available',)
        }),
        ('Additional Info', {
            'fields': ('hospital_affiliation', 'education', 'certifications', 'bio'),
            'classes': ('collapse',)
        }),
        ('Social Links', {
            'fields': ('linkedin_url', 'website_url'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.profile.user.get_full_name()}"
    get_doctor_name.short_description = 'Doctor Name'
    get_doctor_name.admin_order_field = 'profile__user__first_name'
    
    def get_doctor_email(self, obj):
        return obj.profile.user.email
    get_doctor_email.short_description = 'Email'


# ============================================
# PatientProfile Admin
# ============================================
@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = (
        'get_patient_name',
        'get_patient_email',
        'blood_type',
        'insurance_provider',
        'emergency_contact_name',
        'get_age'
    )
    list_filter = ('blood_type', 'insurance_provider')
    search_fields = (
        'profile__user__username',
        'profile__user__email',
        'insurance_provider',
        'emergency_contact_name'
    )
    raw_id_fields = ('profile',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Profile', {
            'fields': ('profile',)
        }),
        ('Medical Information', {
            'fields': ('blood_type',)
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation')
        }),
        ('Insurance', {
            'fields': ('insurance_provider', 'insurance_number', 'insurance_expiry')
        }),
        ('Additional', {
            'fields': ('primary_care_physician',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_patient_name(self, obj):
        return obj.profile.user.get_full_name()
    get_patient_name.short_description = 'Patient Name'
    
    def get_patient_email(self, obj):
        return obj.profile.user.email
    get_patient_email.short_description = 'Email'
    
    def get_age(self, obj):
        if obj.profile.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - obj.profile.date_of_birth.year
        return '-'
    get_age.short_description = 'Age'


# ============================================
# Unregister default User admin
# ============================================
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)