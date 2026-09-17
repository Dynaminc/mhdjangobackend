# apps/prescriptions/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import BaseModel, Profile, DoctorProfile, PatientProfile
from consultations.models import MedicalRecord, Consultation
import uuid
from django.utils import timezone
from datetime import timedelta


# ============================================
# MEDICATION CATALOG - Master list of medications
# ============================================
class MedicationCatalog(BaseModel):
    """Master catalog of all available medications"""
    
    CATEGORY_CHOICES = (
        ('antibiotic', 'Antibiotic'),
        ('antidepressant', 'Antidepressant'),
        ('antianxiety', 'Antianxiety'),
        ('antipsychotic', 'Antipsychotic'),
        ('antihypertensive', 'Antihypertensive'),
        ('antidiabetic', 'Antidiabetic'),
        ('analgesic', 'Analgesic'),
        ('antihistamine', 'Antihistamine'),
        ('antiinflammatory', 'Anti-inflammatory'),
        ('anticoagulant', 'Anticoagulant'),
        ('anticonvulsant', 'Anticonvulsant'),
        ('statin', 'Statin'),
        ('steroid', 'Steroid'),
        ('antiviral', 'Antiviral'),
        ('vitamin', 'Vitamin/Supplement'),
        ('hormone', 'Hormone'),
        ('immunosuppressant', 'Immunosuppressant'),
        ('respiratory', 'Respiratory'),
        ('gastrointestinal', 'Gastrointestinal'),
        ('neurological', 'Neurological'),
        ('psychiatric', 'Psychiatric'),
        ('other', 'Other'),
    )
    
    FORM_CHOICES = (
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('liquid', 'Liquid'),
        ('injection', 'Injection'),
        ('cream', 'Cream/Ointment'),
        ('inhaler', 'Inhaler'),
        ('patch', 'Patch'),
        ('suppository', 'Suppository'),
        ('drops', 'Drops'),
        ('suspension', 'Suspension'),
        ('powder', 'Powder'),
        ('other', 'Other'),
    )
    
    SCHEDULE_CHOICES = (
        ('i', 'Schedule I'),
        ('ii', 'Schedule II'),
        ('iii', 'Schedule III'),
        ('iv', 'Schedule IV'),
        ('v', 'Schedule V'),
        ('unscheduled', 'Unscheduled'),
    )
    
    # Basic info
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique medication code (e.g., MED-001)"
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Generic name of the medication"
    )
    brand_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Brand/trade name"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        db_index=True,
        help_text="Medication category"
    )
    
    # Form and administration
    form = models.CharField(
        max_length=20,
        choices=FORM_CHOICES,
        default='tablet',
        help_text="Form of the medication"
    )
    route_of_administration = models.CharField(
        max_length=100,
        blank=True,
        help_text="Route of administration (e.g., oral, IV, topical)"
    )
    
    # Dosage
    default_dosage = models.CharField(
        max_length=50,
        blank=True,
        help_text="Default dosage (e.g., 50mg)"
    )
    dosage_unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Dosage unit (e.g., mg, mcg, mL)"
    )
    dosage_form = models.CharField(
        max_length=100,
        blank=True,
        help_text="Dosage form (e.g., 50mg tablet)"
    )
    
    # Strength
    strength = models.CharField(
        max_length=50,
        blank=True,
        help_text="Medication strength"
    )
    concentration = models.CharField(
        max_length=50,
        blank=True,
        help_text="Concentration for liquid forms"
    )
    
    # Controlled substance
    schedule = models.CharField(
        max_length=20,
        choices=SCHEDULE_CHOICES,
        default='unscheduled',
        help_text="DEA schedule"
    )
    is_controlled = models.BooleanField(
        default=False,
        help_text="Whether this is a controlled substance"
    )
    requires_prescription = models.BooleanField(
        default=True,
        help_text="Whether this requires a prescription"
    )
    
    # Interactions and warnings
    contraindications = models.TextField(
        blank=True,
        help_text="Contraindications for this medication"
    )
    warnings = models.TextField(
        blank=True,
        help_text="Warnings and precautions"
    )
    side_effects = models.TextField(
        blank=True,
        help_text="Common side effects"
    )
    interactions = models.TextField(
        blank=True,
        help_text="Drug interactions"
    )
    
    # Pregnancy and breastfeeding
    pregnancy_category = models.CharField(
        max_length=10,
        blank=True,
        help_text="FDA pregnancy category (A, B, C, D, X)"
    )
    breastfeeding_safety = models.TextField(
        blank=True,
        help_text="Breastfeeding safety information"
    )
    
    # Cost
    average_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Average cost per unit"
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this medication is currently available"
    )
    requires_monitoring = models.BooleanField(
        default=False,
        help_text="Whether this medication requires monitoring"
    )
    monitoring_tests = models.TextField(
        blank=True,
        help_text="Recommended monitoring tests"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the medication"
    )
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.get_category_display()})"
    
    def get_full_name(self):
        if self.brand_name:
            return f"{self.name} ({self.brand_name})"
        return self.name
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['code', 'name']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]


# ============================================
# PRESCRIPTION
# ============================================
# apps/prescriptions/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
from accounts.models import BaseModel, DoctorProfile, PatientProfile


class Prescription(BaseModel):
    """Medication prescription issued by a doctor"""

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )

    FREQUENCY_CHOICES = (
        ('once_daily', 'Once daily'),
        ('twice_daily', 'Twice daily'),
        ('three_times_daily', 'Three times daily'),
        ('four_times_daily', 'Four times daily'),
        ('every_6_hours', 'Every 6 hours'),
        ('every_8_hours', 'Every 8 hours'),
        ('every_12_hours', 'Every 12 hours'),
        ('once_weekly', 'Once weekly'),
        ('twice_weekly', 'Twice weekly'),
        ('as_needed', 'As needed'),
        ('other', 'Other'),
    )

    DURATION_UNIT_CHOICES = (
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('indefinite', 'Indefinite'),
    )

    # -------------------------------------------------
    # Relationships
    # -------------------------------------------------
    prescription_number = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text="Auto-generated (e.g., RX-2026-0001)"
    )
    patient_profile = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    doctor_profile = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE,
        related_name='prescriptions'
    )

    # -------------------------------------------------
    # Medication (frontend sends only the name)
    # -------------------------------------------------
    medication_name = models.CharField(
        max_length=255,
        help_text="Name of the medication"
    )

    # -------------------------------------------------
    # Dosage & instructions
    # -------------------------------------------------
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(
        max_length=50, choices=FREQUENCY_CHOICES, default='once_daily'
    )
    frequency_custom = models.CharField(max_length=100, blank=True)

    duration_value = models.IntegerField(default=30)
    duration_unit = models.CharField(
        max_length=20, choices=DURATION_UNIT_CHOICES, default='days'
    )

    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    refills = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(12)]
    )
    refills_used = models.IntegerField(default=0)

    instructions = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)

    # -------------------------------------------------
    # Dates
    # -------------------------------------------------
    prescribed_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    last_filled_date = models.DateTimeField(null=True, blank=True)

    # -------------------------------------------------
    # Status
    # -------------------------------------------------
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='active', db_index=True
    )

    # -------------------------------------------------
    # Pharmacy (optional)
    # -------------------------------------------------
    pharmacy_name = models.CharField(max_length=255, blank=True)
    pharmacy_phone = models.CharField(max_length=20, blank=True)
    pharmacy_address = models.TextField(blank=True)

    # -------------------------------------------------
    # Auto-numbering & expiry
    # -------------------------------------------------
    def save(self, *args, **kwargs):
        if not self.prescription_number:
            year = timezone.now().year
            count = Prescription.objects.filter(
                created_at__year=year
            ).count() + 1
            self.prescription_number = f"RX-{year}-{str(count).zfill(4)}"

        if not self.expiry_date and self.duration_value and self.duration_unit:
            today = timezone.now().date()
            if self.duration_unit == 'days':
                self.expiry_date = today + timedelta(days=self.duration_value)
            elif self.duration_unit == 'weeks':
                self.expiry_date = today + timedelta(weeks=self.duration_value)
            elif self.duration_unit == 'months':
                self.expiry_date = today + timedelta(days=self.duration_value * 30)

        super().save(*args, **kwargs)

    # -------------------------------------------------
    # Status helpers
    # -------------------------------------------------
    def suspend(self):
        self.status = 'suspended'
        self.save()

    def resume(self):
        self.status = 'active'
        self.save()

    def cancel(self):
        self.status = 'cancelled'
        self.save()

    def complete(self):
        self.status = 'completed'
        self.save()

    def can_refill(self):
        if self.status != 'active':
            return False
        if self.refills_used >= self.refills:
            return False
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False
        return True

    def use_refill(self):
        if self.can_refill():
            self.refills_used += 1
            self.last_filled_date = timezone.now()
            self.save()
            return True
        return False

    # -------------------------------------------------
    # Properties
    # -------------------------------------------------
    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def duration_display(self):
        return f"{self.duration_value} {self.get_duration_unit_display()}"

    @property
    def frequency_display(self):
        if self.frequency == 'other':
            return self.frequency_custom
        return self.get_frequency_display()

    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        return f"{self.prescription_number} - {self.medication_name} - {patient_name}"

    class Meta:
        ordering = ['-prescribed_date']
        indexes = [
            models.Index(fields=['prescription_number']),
            models.Index(fields=['patient_profile', 'status']),
            models.Index(fields=['doctor_profile', 'status']),
            models.Index(fields=['prescribed_date']),
        ]

# ============================================
# PRESCRIPTION REFILL REQUEST
# ============================================
class RefillRequest(BaseModel):
    """Patient requests for prescription refills"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='refill_requests',
        help_text="The prescription being refilled"
    )
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='refill_requests',
        help_text="The patient requesting the refill"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Status of the request"
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for refill request"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    requested_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date the request was reviewed"
    )
    reviewed_by = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_refills',
        help_text="Doctor who reviewed the request"
    )
    review_notes = models.TextField(
        blank=True,
        help_text="Review notes"
    )
    
    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        return f"Refill request for {self.prescription.prescription_number} - {patient_name}"
    
    def approve(self, doctor):
        """Approve the refill request"""
        self.status = 'approved'
        self.reviewed_by = doctor
        self.reviewed_date = timezone.now()
        self.save()
        # Use a refill
        self.prescription.use_refill()
    
    def reject(self, doctor, reason=''):
        """Reject the refill request"""
        self.status = 'rejected'
        self.reviewed_by = doctor
        self.reviewed_date = timezone.now()
        self.review_notes = reason
        self.save()
    
    class Meta:
        ordering = ['-requested_date']
        indexes = [
            models.Index(fields=['prescription', 'status']),
            models.Index(fields=['patient_profile', 'status']),
        ]


# ============================================
# MEDICATION INTERACTION
# ============================================
class MedicationInteraction(BaseModel):
    """Drug-drug interactions between medications"""
    
    SEVERITY_CHOICES = (
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('contraindicated', 'Contraindicated'),
    )
    
    medication_a = models.ForeignKey(
        MedicationCatalog,
        on_delete=models.CASCADE,
        related_name='interactions_as_a',
        help_text="First medication"
    )
    medication_b = models.ForeignKey(
        MedicationCatalog,
        on_delete=models.CASCADE,
        related_name='interactions_as_b',
        help_text="Second medication"
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='moderate',
        help_text="Severity of the interaction"
    )
    description = models.TextField(
        help_text="Description of the interaction"
    )
    mechanism = models.TextField(
        blank=True,
        help_text="Mechanism of the interaction"
    )
    management = models.TextField(
        blank=True,
        help_text="How to manage the interaction"
    )
    
    def __str__(self):
        return f"{self.medication_a.name} - {self.medication_b.name}: {self.get_severity_display()}"
    
    class Meta:
        unique_together = ['medication_a', 'medication_b']
        indexes = [
            models.Index(fields=['medication_a', 'severity']),
            models.Index(fields=['medication_b', 'severity']),
        ]


# ============================================
# MEDICATION ADMINISTRATION SCHEDULE
# ============================================
class MedicationSchedule(BaseModel):
    """Detailed administration schedule for a prescription"""
    
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='schedules',
        help_text="The prescription this schedule belongs to"
    )
    
    day_of_week = models.IntegerField(
        choices=[
            (0, 'Sunday'),
            (1, 'Monday'),
            (2, 'Tuesday'),
            (3, 'Wednesday'),
            (4, 'Thursday'),
            (5, 'Friday'),
            (6, 'Saturday'),
        ],
        help_text="Day of the week"
    )
    time = models.TimeField(
        help_text="Time of administration"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes about this administration"
    )
    
    def __str__(self):
        return f"{self.prescription.prescription_number} - Day {self.day_of_week} at {self.time}"


# ============================================
# MEDICATION ADHERENCE TRACKING
# ============================================
class MedicationAdherence(BaseModel):
    """Track patient adherence to medication regimen"""
    
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='adherence_records',
        help_text="The prescription being tracked"
    )
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='adherence_records',
        help_text="The patient being tracked"
    )
    
    date = models.DateField(
        help_text="Date of adherence record"
    )
    taken = models.BooleanField(
        default=False,
        help_text="Whether the medication was taken"
    )
    time_taken = models.TimeField(
        null=True,
        blank=True,
        help_text="Time the medication was taken"
    )
    skipped_reason = models.TextField(
        blank=True,
        help_text="Reason if medication was skipped"
    )
    side_effects = models.TextField(
        blank=True,
        help_text="Any side effects experienced"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        med_name = self.prescription.medication_name
        return f"{patient_name} - {med_name} - {self.date}"
    
    class Meta:
        unique_together = ['prescription', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['patient_profile', 'date']),
            models.Index(fields=['prescription', 'date']),
        ]

