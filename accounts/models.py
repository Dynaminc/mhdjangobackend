# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

# ============================================
# Base Model (moved here since core is removed)
# ============================================
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


# ======================================# apps/users/models.py
from django.contrib.auth.models import User as DjangoUser
from django.db import models

# ============================================
# Base Model
# ============================================
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


# ============================================
# Profile Model (Core user profile)
# ============================================
class Profile(BaseModel):
    """Core user profile linked to Django's default User"""
    
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    )
    
    user = models.OneToOneField(
        DjangoUser, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    mh_user_id = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True,
        help_text="Unique MHPro user identifier (e.g., MH-2026-0001)"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    
    # ✅ New field
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
        # ✅ Track how the user signed up
    SIGNUP_METHOD_CHOICES = (
        ('email', 'Email'),
        ('google', 'Google'),
    )
    signup_method = models.CharField(
        max_length=20,
        choices=SIGNUP_METHOD_CHOICES,
        default='email',
    )
    
    # Additional profile fields
    phone = models.CharField(max_length=20, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    country = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_logout_at = models.DateTimeField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    is_online = models.BooleanField(default=False)
    
    # Profile picture
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        null=True, 
        blank=True
    )
    
    # Bio
    bio = models.TextField(blank=True)
    
    # Preferences
    language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    notifications_enabled = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"
    
    @property
    def is_doctor(self):
        return hasattr(self, 'doctor_profile')
    
    @property
    def is_patient(self):
        return hasattr(self, 'patient_profile')
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    def get_role_display_name(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['is_online']),
        ]


# ============================================
# Doctor Profile (extends Profile)
# ============================================
class DoctorProfile(BaseModel):
    """Doctor-specific information extending Profile"""
    
    profile = models.OneToOneField(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='doctor_profile'
    )
    
    # Doctor-specific fields
    specialty = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, null=True, blank=True )
    years_experience = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    # Availability
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=85.00)
    is_available = models.BooleanField(default=True)
    
    # Professional details
    hospital_affiliation = models.CharField(max_length=255, blank=True)
    education = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    
    # Social links
    linkedin_url = models.URLField(max_length=200, blank=True)
    website_url = models.URLField(max_length=200, blank=True)
    
    def __str__(self):
        return f"Dr. {self.profile.user.get_full_name()} - {self.specialty}"
    
    def get_rating(self):
        if self.rating:
            return float(self.rating)
        return 0.0
    
    def update_rating(self):
        from django.db.models import Avg
        # Assuming you have a Review model
        # avg = Review.objects.filter(doctor=self).aggregate(Avg('rating'))['rating__avg']
        # if avg:
        #     self.rating = round(avg, 2)
        #     self.save()
        pass


# ============================================
# Patient Profile (extends Profile)
# ============================================
class PatientProfile(BaseModel):
    """Patient-specific information extending Profile"""
    
    profile = models.OneToOneField(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='patient_profile'
    )
    
    # Patient-specific fields
    blood_type = models.CharField(max_length=5, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    
    # Insurance
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_number = models.CharField(max_length=50, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    
    # Medical
    primary_care_physician = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"{self.profile.user.get_full_name()} (Patient)"
    
    def get_emergency_contact(self):
        if self.emergency_contact_name:
            return f"{self.emergency_contact_name} ({self.emergency_contact_relation}) - {self.emergency_contact_phone}"
        return "No emergency contact provided"


# ============================================
# User Signals - Auto create profile
# ============================================
# from django.db.models.signals import post_save
# from django.dispatch import receiver

# @receiver(post_save, sender=DjangoUser)
# def create_user_profile(sender, instance, created, **kwargs):
#     """Auto-create a Profile when a Django User is created"""
#     if created:
#         Profile.objects.create(user=instance)

# @receiver(post_save, sender=DjangoUser)
# def save_user_profile(sender, instance, **kwargs):
#     """Save Profile when User is saved"""
#     try:
#         instance.profile.save()
#     except Profile.DoesNotExist:
#         Profile.objects.create(user=instance)