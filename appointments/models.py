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

from notifications.models import NotificationSignalHandler
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save

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
        default=False,
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


# class DoctorAvailability(BaseModel):
#     """Doctor's availability schedule"""
#     doctor_profile = models.ForeignKey(
#         DoctorProfile,
#         on_delete=models.CASCADE,
#         related_name='availability'
#     )
    
#     DAY_CHOICES = (
#         (0, 'Monday'),
#         (1, 'Tuesday'),
#         (2, 'Wednesday'),
#         (3, 'Thursday'),
#         (4, 'Friday'),
#         (5, 'Saturday'),
#         (6, 'Sunday'),
#     )
    
#     day_of_week = models.IntegerField(choices=DAY_CHOICES)
#     start_time = models.TimeField()
#     end_time = models.TimeField()
#     is_available = models.BooleanField(default=True)
    
#     # Optional: specific date override
#     specific_date = models.DateField(null=True, blank=True)
    
#     class Meta:
#         ordering = ['day_of_week', 'start_time']
    
#     def __str__(self):
#         return f"{self.doctor_profile} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Appointment(BaseModel):
    """Appointment booking"""
    
    STATUS_CHOICES = (
        ('awaiting', 'Awaiting Approval'),
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
        related_name='appointments',
        null=True,  # Allow NULL for first-available pattern
        blank=True, 
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
        default='awaiting'
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
    
    def is_active(self):
        """Check if queue entry is active AND patient is online"""
        if self.status not in ['awaiting', 'scheduled', 'confirmed']:
            return True    
        return False
    
    def cancel(self):
        self.status = 'cancelled'
        self.save()    
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
        
        
        
        
# notifications/models.py  (appointment + queue receivers only)


# ============================================
# APPOINTMENT NOTIFICATIONS
# ============================================
@receiver(post_save, sender='appointments.Appointment')
def handle_appointment_notification(sender, instance, created, **kwargs):
    """
    Notifications for every Appointment transition:

        created                      → patient + doctor
        doctor assigned (unchanged)  → patient + new doctor
        status → confirmed           → patient
        status → in_progress         → patient
        status → completed           → patient
        status → cancelled           → patient + doctor
        status → no_show             → patient + doctor

    Reads `_previous_status` / `_previous_doctor_id`, which are set by
    apps.appointments.signals.track_appointment_previous_state.
    """
    handler = NotificationSignalHandler()

    # ── Resolve users (guarded — either side may be absent) ───
    patient_user = (
        instance.patient_profile.profile.user
        if instance.patient_profile_id else None
    )
    doctor_user = (
        instance.doctor_profile.profile.user
        if instance.doctor_profile_id else None
    )

    if not patient_user and not doctor_user:
        return

    patient_name = (
        patient_user.get_full_name() or patient_user.username
        if patient_user else "the patient"
    )
    doctor_name = (
        f"Dr. {doctor_user.get_full_name() or doctor_user.username}"
        if doctor_user else "your doctor"
    )
    when = f"{instance.appointment_date} at {instance.start_time}"

    def _mk(user, ntype, title, msg, priority='medium'):
        if user is None:
            return None
        return handler.create_notification(
            user=user,
            notification_type=ntype,
            title=title,
            message=msg,
            priority=priority,
            related_object_id=str(instance.id),
            related_object_type='appointment',
            related_url=f'/appointments/{instance.id}/',
            data={
                'appointment_id': instance.id,
                'status': instance.status,
                'appointment_date': str(instance.appointment_date),
                'start_time': str(instance.start_time),
            },
        )

    previous_status = getattr(instance, '_previous_status', None)
    previous_doctor_id = getattr(instance, '_previous_doctor_id', None)

    # ── 1. Creation ───────────────────────────────────────────
    if created:
        _mk(
            patient_user, 'appointment_created',
            'Appointment Scheduled',
            f"Your appointment on {when} has been scheduled.",
        )
        _mk(
            doctor_user, 'appointment_created',
            'New Appointment',
            f"New appointment with {patient_name} on {when}.",
            priority='high',
        )
        return

    # ── 2. Doctor just assigned to an existing appointment ────
    doctor_just_assigned = (
        instance.doctor_profile_id is not None
        and previous_doctor_id != instance.doctor_profile_id
    )
    if doctor_just_assigned:
        _mk(
            doctor_user, 'appointment_created',
            'New Appointment Assigned',
            f"You have been assigned to see {patient_name} on {when}.",
            priority='high',
        )
        _mk(
            patient_user, 'appointment_confirmed',
            'Doctor Assigned',
            f"{doctor_name} will see you on {when}.",
        )

    # ── 3. Status transitions (only on real change) ───────────
    if previous_status == instance.status:
        return

    if instance.status == 'confirmed':
        _mk(
            patient_user, 'appointment_confirmed',
            'Appointment Confirmed',
            f"Your appointment with {doctor_name} on {when} has been confirmed.",
        )

    elif instance.status == 'in_progress':
        _mk(
            patient_user, 'appointment_reminder',
            'Appointment Starting',
            f"Your appointment with {doctor_name} is starting now.",
            priority='high',
        )

    elif instance.status == 'completed':
        _mk(
            patient_user, 'appointment_completed',
            'Appointment Completed',
            f"Your appointment with {doctor_name} on {when} is complete.",
        )

    elif instance.status == 'cancelled':
        _mk(
            patient_user, 'appointment_cancelled',
            'Appointment Cancelled',
            f"Your appointment with {doctor_name} on {when} has been cancelled.",
            priority='high',
        )
        _mk(
            doctor_user, 'appointment_cancelled',
            'Appointment Cancelled',
            f"Appointment with {patient_name} on {when} has been cancelled.",
        )

    elif instance.status == 'no_show':
        _mk(
            patient_user, 'appointment_no_show',
            'No-Show Recorded',
            f"You were marked as a no-show for {when}.",
        )
        _mk(
            doctor_user, 'appointment_no_show',
            'No-Show Recorded',
            f"{patient_name} did not attend {when}.",
        )


# ============================================
# QUEUE ENTRY NOTIFICATIONS
# ============================================
@receiver(post_save, sender='appointments.QueueEntry')
def handle_queue_notification(sender, instance, created, **kwargs):
    """
    Notifications for the QueueEntry model path.

    NOTE: QueueViewSet uses an in-memory queue_service and does NOT write
    QueueEntry rows. For those actions, call
    notifications.helpers.notify_queue_event(...) directly from the view.
    This handler only fires for the legacy QueueEntryViewSet path.
    """
    handler = NotificationSignalHandler()

    if not instance.patient_profile_id:
        return

    patient_user = instance.patient_profile.profile.user

    def _mk(ntype, title, msg, priority='medium'):
        return handler.create_notification(
            user=patient_user,
            notification_type=ntype,
            title=title,
            message=msg,
            priority=priority,
            related_object_id=str(instance.id),
            related_object_type='queue',
            related_url='/queue/',
            data={
                'queue_entry_id': instance.id,
                'queue_position': instance.queue_position,
                'wait_time_minutes': instance.wait_time_minutes,
            },
        )

    if created:
        _mk(
            'queue_waiting',
            'Added to Queue',
            f"You are in position {instance.queue_position} in the queue. "
            f"Estimated wait: {instance.wait_time_minutes} minutes.",
        )
        return

    if instance.status == 'admitted':
        _mk(
            'queue_admitted',
            '✅ Admitted from Queue',
            "You have been admitted. Your consultation will begin shortly.",
            priority='high',
        )
        return

    previous_position = getattr(instance, '_original_queue_position', None)
    if previous_position is not None and instance.queue_position != previous_position:
        _mk(
            'queue_position_updated',
            'Queue Position Updated',
            f"You are now at position {instance.queue_position}. "
            f"Estimated wait: {instance.wait_time_minutes} minutes.",
            priority='low',
        )        