# apps/appointments/models.py
from django.db import models
from django.contrib.auth.models import User
from accounts.models import BaseModel, Profile, DoctorProfile, PatientProfile
from django.utils import timezone
from django.db.models import Max
from django.core.cache import cache
# apps/appointments/models.py
from django.db import models
from accounts.models import BaseModel, Profile, DoctorProfile, PatientProfile

class Clinic(BaseModel):
    """Medical clinic/facility"""
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    
    # A clinic can have multiple doctors
    doctors = models.ManyToManyField(
        DoctorProfile,
        related_name='clinics',
        blank=True,
        help_text="Doctors working at this clinic"
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    appointment_duration = models.IntegerField(
        default=30,
        help_text="Default appointment duration in minutes"
    )
    allow_online_booking = models.BooleanField(default=True)
    requires_doctor_selection = models.BooleanField(
        default=True,
        help_text="If True, patients must select a doctor. If False, system assigns."
    )
    
    def __str__(self):
        return self.name
    
    @property
    def doctor_count(self):
        return self.doctors.count()
    
    @property
    def has_multiple_doctors(self):
        return self.doctors.count() > 1
    
    @property
    def available_doctors(self):
        """Get doctors available for new appointments"""
        return self.doctors.filter(availabilities__is_available=True).distinct()
        # return self.doctors.filter(
        #     availability__is_available=True
        # ).distinct()


class DoctorAvailability(BaseModel):
    """Doctor's availability schedule"""
    doctor_profile = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='availability'
    )
    
    DAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    # Optional: specific date override
    specific_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.doctor_profile} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Appointment(BaseModel):
    """Appointment booking"""
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )
    
    TYPE_CHOICES = (
        ('virtual', 'Virtual'),
        ('physical', 'Physical'),
    )
    
    # Core relationships
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    
    # 👇 This can be NULL initially if doctor assignment is deferred
    doctor_profile = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,  # Allow NULL for first-available pattern
        blank=True,
        related_name='appointments',
        help_text="The doctor for this appointment. Can be NULL until assigned."
    )
    
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    
    # Appointment details
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='physical'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    
    # Additional fields
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # For deferred doctor assignment
    doctor_assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the doctor was assigned (if deferred)"
    )
    doctor_assigned_by = models.ForeignKey(
        'accounts.DoctorProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_appointments',
        help_text="Who assigned the doctor (admin/algorithm)"
    )
    
    def __str__(self):
        doctor_name = self.doctor_profile.profile.user.get_full_name() if self.doctor_profile else "Unassigned"
        patient_name = self.patient_profile.profile.user.get_full_name()
        return f"{patient_name} - {doctor_name} - {self.appointment_date}"
    
    def assign_doctor(self, doctor_profile, assigned_by=None):
        """Assign a doctor to this appointment"""
        self.doctor_profile = doctor_profile
        self.doctor_assigned_at = timezone.now()
        self.doctor_assigned_by = assigned_by
        self.save()
    
    @property
    def is_doctor_assigned(self):
        return self.doctor_profile is not None
    
    @property
    def appointment_display(self):
        doctor = self.doctor_profile.profile.user.get_full_name() if self.doctor_profile else "No doctor assigned"
        return f"{self.appointment_date} {self.start_time}-{self.end_time} with {doctor} at {self.clinic.name}"

# ============================================
# Queue Entry Model
# ============================================

class QueueEntry(BaseModel):
    """Queue management for instant consultations"""
    
    STATUS_CHOICES = (
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('admitted', 'Admitted'),
        ('cancelled', 'Cancelled'),
    )
    
    URGENCY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    # Relationships
    patient_profile = models.OneToOneField(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='queue_entry'
    )
    doctor_profile = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='queue_entries',
        null=True,
        blank=True,
    )
    
    # Queue details
    queue_position = models.IntegerField(
        null=True,
        blank=True,
        help_text="Position in the queue (auto-assigned)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='waiting',
        db_index=True
    )
    reason = models.TextField()
    wait_time_minutes = models.IntegerField(default=0)
    admitted_at = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    priority = models.IntegerField(
        default=0,
        help_text="Higher number = higher priority"
    )
    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium'
    )
    
    # Heartbeat fields
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the patient confirmed they're still waiting"
    )
    is_online = models.BooleanField(
        default=True,
        help_text="Whether the patient is currently online"
    )
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp"""
        self.last_heartbeat = timezone.now()
        self.is_online = True
        self.save(update_fields=['last_heartbeat', 'is_online'])
    
    def check_online_status(self):
        """Check if patient is still online based on heartbeat"""
        if self.last_heartbeat:
            time_since = timezone.now() - self.last_heartbeat
            if time_since.total_seconds() > 120:  # 2 minutes
                self.is_online = False
                self.save(update_fields=['is_online'])
                return False
        return True
    
    @property
    def is_active(self):
        """Check if queue entry is active AND patient is online"""
        if self.status not in ['waiting', 'in_progress']:
            return False
        if self.status == 'waiting':
            return self.is_online
        return True
    
    def admit(self):
        self.status = 'admitted'
        self.admitted_at = timezone.now()
        self.save()
    
    def start_progress(self):
        self.status = 'in_progress'
        self.save()
    
    def cancel(self):
        self.status = 'cancelled'
        self.save()
    
    def update_wait_time(self):
        if self.created_at and self.status == 'waiting':
            elapsed = timezone.now() - self.created_at
            self.wait_time_minutes = int(elapsed.total_seconds() / 60)
            self.save(update_fields=['wait_time_minutes'])
    
    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        return f"{patient_name} - Position {self.queue_position} - {self.status}"
    
    class Meta:
        ordering = ['-priority', 'queue_position']
        indexes = [
            models.Index(fields=['status', 'queue_position']),
            models.Index(fields=['patient_profile', 'status']),
            models.Index(fields=['doctor_profile', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['urgency_level', 'status']),
        ]
# ============================================



# Appointment Availability (Optional)
# ============================================
class DoctorAvailability(BaseModel):
    """Doctor's available time slots"""
    
    DAYS_OF_WEEK = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )
    
    doctor_profile = models.ForeignKey(
        DoctorProfile, 
        on_delete=models.CASCADE, 
        related_name='availabilities'
    )
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    # Break times
    specific_date = models.DateField(null=True, blank=True)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.doctor_profile} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['doctor_profile', 'day_of_week', 'start_time', 'end_time']