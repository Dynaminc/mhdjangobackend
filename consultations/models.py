# apps/consultations/models.py
from django.db import models
from accounts.models import BaseModel, Profile, DoctorProfile, PatientProfile
from appointments.models import Appointment
import uuid


# ============================================
# CONSULTATION - The actual clinical encounter
# ============================================
class Consultation(BaseModel):
    """A single consultation/visit with a patient."""
    
    TYPE_CHOICES = (
        ('virtual', 'Virtual'),
        ('physical', 'Physical'),
    )
    STATUS_CHOICES = (
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    # Relationships
    appointment = models.OneToOneField(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='consultation',
        null=True,
        blank=True,
        help_text="The appointment that generated this consultation"
    )
    patient_profile = models.ForeignKey(
        PatientProfile, 
        on_delete=models.CASCADE, 
        related_name='consultations',
        help_text="The patient being consulted"
    )
    doctor_profile = models.ForeignKey(
        DoctorProfile, 
        on_delete=models.CASCADE, 
        related_name='consultations',
        help_text="The doctor conducting the consultation"
    )
    
    # Clinical Data - What happened during this specific consultation
    hpc = models.TextField(
        blank=True, 
        help_text="History of Presenting Complaint - Patient's story of their current problem"
    )
    symptoms = models.TextField(
        blank=True, 
        help_text="Patient reported symptoms"
    )
    duration = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Duration of symptoms"
    )
    vitals = models.TextField(
        blank=True, 
        help_text="Vital signs recorded during consultation"
    )
    assessment = models.TextField(
        blank=True, 
        help_text="Clinical assessment/diagnosis"
    )
    plan = models.TextField(
        blank=True, 
        help_text="Treatment plan and next steps"
    )
    
    # Metadata
    type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default='virtual',
        help_text="Virtual or physical consultation"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='ongoing', 
        db_index=True,
        help_text="Current status of the consultation"
    )
    
    # Clinic info for physical consultations
    clinic_location = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Clinic location for physical consultations"
    )
    
    # Chat reference
    chat_conversation_id = models.CharField(
        max_length=36,
        blank=True,
        null=True,
        help_text="Reference to the chat conversation in Flask chat server"
    )
    
    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        doctor_name = self.doctor_profile.profile.user.get_full_name()
        return f"Consultation #{self.id} - {patient_name} with Dr. {doctor_name}"
    
    @property
    def patient(self):
        """Property to maintain compatibility with old code"""
        return self.patient_profile
    
    @property
    def doctor(self):
        """Property to maintain compatibility with old code"""
        return self.doctor_profile
    
    @property
    def is_virtual(self):
        return self.type == 'virtual'
    
    @property
    def is_physical(self):
        return self.type == 'physical'
    
    @property
    def is_ongoing(self):
        return self.status == 'ongoing'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    def complete(self):
        """Mark consultation as completed"""
        from django.utils import timezone
        self.status = 'completed'
        self.save()
        # Trigger medical record update
        # from .signals import update_medical_record_on_consultation
        update_medical_record_on_consultation(self)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_profile', 'status']),
            models.Index(fields=['doctor_profile', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['type']),
        ]


# ============================================
# EXAMINATION - Physical examination findings
# ============================================
class Examination(BaseModel):
    """
    Physical examination findings for a consultation.
    Each consultation can have multiple examinations.
    Only relevant for physical consultations.
    """
    
    EXAMINATION_TYPES = (
        ('general', 'General Appearance'),
        ('vitals', 'Vitals'),
        ('head_neck', 'Head & Neck'),
        ('chest', 'Chest'),
        ('heart', 'Cardiovascular'),
        ('abdomen', 'Abdomen'),
        ('pelvic', 'Pelvic'),
        ('musculoskeletal', 'Musculoskeletal'),
        ('neurological', 'Neurological'),
        ('dermatological', 'Skin'),
        ('psychiatric', 'Psychiatric/Mental Status'),
        ('other', 'Other'),
    )
    
    # Relationship to consultation
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='examinations',
        help_text="The consultation this examination belongs to"
    )
    
    # Examination details
    examination_type = models.CharField(
        max_length=50,
        choices=EXAMINATION_TYPES,
        db_index=True,
        help_text="Type of examination performed"
    )
    
    # Findings
    findings = models.TextField(
        help_text="Detailed findings from the examination"
    )
    
    # Normal/Abnormal flag
    is_normal = models.BooleanField(
        default=True,
        help_text="Whether the findings are normal"
    )
    
    # Additional notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the examination"
    )
    
    # For specific examinations
    bp_systolic = models.IntegerField(null=True, blank=True, help_text="Blood Pressure Systolic")
    bp_diastolic = models.IntegerField(null=True, blank=True, help_text="Blood Pressure Diastolic")
    heart_rate = models.IntegerField(null=True, blank=True, help_text="Heart Rate (bpm)")
    respiratory_rate = models.IntegerField(null=True, blank=True, help_text="Respiratory Rate")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Temperature (°C)")
    spo2 = models.IntegerField(null=True, blank=True, help_text="Oxygen Saturation (%)")
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Weight (kg)")
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height (cm)")
    
    def __str__(self):
        return f"{self.get_examination_type_display()} - {self.consultation}"
    
    @property
    def bmi(self):
        """Calculate BMI if weight and height are available"""
        if self.weight and self.height:
            height_m = self.height / 100
            return round(self.weight / (height_m * height_m), 1)
        return None
    
    @property
    def is_vital_sign(self):
        """Check if this is a vital signs examination"""
        return self.examination_type == 'vitals'
    
    class Meta:
        ordering = ['examination_type', '-created_at']
        indexes = [
            models.Index(fields=['consultation', 'examination_type']),
            models.Index(fields=['consultation', 'is_normal']),
        ]


# ============================================
# PAST MEDICAL HISTORY - Static patient background
# ============================================
# apps/consultations/models.py# apps/consultations/models.py

class PastMedicalHistory(BaseModel):
    """Patient's static medical history (PMH)"""
    
    HISTORY_TYPES = (
        ('general', 'General Medical History'),
        ('surgical', 'Surgical History'),
        ('gynecological', 'Gynecological History'),
        ('obstetric', 'Obstetric History'),
        ('nutritional', 'Nutritional History'),
        ('developmental', 'Developmental History'),
        ('psychosocial', 'Psychosocial History'),
        ('family', 'Family History'),
        ('social', 'Social History'),
        ('allergy', 'Allergies'),
        ('medication', 'Current Medications'),
        ('immunization', 'Immunization History'),
    )
    
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='past_medical_histories',
    )
    history_type = models.CharField(max_length=50, choices=HISTORY_TYPES, db_index=True)
    content = models.TextField()
    recorded_by = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_histories',
    )
    recorded_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_history_type_display()} - {self.patient_profile.profile.user.get_full_name()}"

    class Meta:
        ordering = ['history_type', '-created_at']
        
        
# ============================================
# MEDICAL RECORD - Aggregates everything about a patient
# ============================================
class MedicalRecord(BaseModel):
    """
    The comprehensive medical record for a patient.
    THIS IS THE AGGREGATE - it pulls everything together.
    """
    
    # The patient this record belongs to
    patient_profile = models.OneToOneField(
        PatientProfile, 
        on_delete=models.CASCADE, 
        related_name='medical_record',
        help_text="The patient this medical record belongs to"
    )
    
    # Meta information
    record_number = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Unique medical record number (e.g., MRN-2026-001)"
    )
    last_updated_by = models.ForeignKey(
        DoctorProfile, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='updated_medical_records',
        help_text="Doctor who last updated this record"
    )
    
    # Summary/computed fields
    active_problems = models.TextField(
        blank=True,
        help_text="List of active medical problems"
    )
    active_medications_summary = models.TextField(
        blank=True,
        help_text="Summary of current medications"
    )
    allergies_summary = models.TextField(
        blank=True,
        help_text="Summary of known allergies"
    )
    
    # Clinical flags
    is_complete = models.BooleanField(
        default=False,
        help_text="Whether the record is complete"
    )
    last_review_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date of last review"
    )
    
    # ============================================
    # PROPERTIES - Access aggregated data
    # ============================================
    
    @property
    def patient(self):
        """Property to maintain compatibility with old code"""
        return self.patient_profile
    
    @property
    def all_consultations(self):
        """Get all consultations for this patient."""
        return self.patient_profile.consultations.all()
    
    @property
    def past_medical_histories(self):
        """Get all past medical histories for this patient."""
        return self.patient_profile.past_medical_histories.filter(is_active=True)
    
    @property
    def all_medications(self):
        """Get all prescriptions for this patient."""
        return self.patient_profile.prescriptions.filter(status='active')
    
    @property
    def all_lab_tests(self):
        """Get all lab tests for this patient."""
        return self.patient_profile.lab_tests.all()
    
    @property
    def all_examinations(self):
        """Get all examinations from all consultations."""
        examinations = []
        for consultation in self.patient_profile.consultations.all():
            examinations.extend(consultation.examinations.all())
        return examinations
    
    @property
    def recent_consultations(self):
        """Get recent consultations (last 30 days)."""
        from django.utils import timezone
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return self.patient_profile.consultations.filter(
            created_at__gte=thirty_days_ago
        )
    
    @property
    def demographic_info(self):
        """Get patient demographic information."""
        profile = self.patient_profile.profile
        user = profile.user
        return {
            'name': user.get_full_name(),
            'age': profile.age,
            'gender': profile.gender,
            'email': user.email,
            'phone': profile.phone,
            'date_of_birth': profile.date_of_birth,
            'blood_type': self.patient_profile.blood_type,
        }
    
    @property
    def gynecological_history(self):
        """Get gynecological history."""
        return self.patient_profile.past_medical_histories.filter(
            history_type='gynecological',
            is_active=True
        ).first()
    
    @property
    def obstetric_history(self):
        """Get obstetric history."""
        return self.patient_profile.past_medical_histories.filter(
            history_type='obstetric',
            is_active=True
        ).first()
    
    @property
    def psychosocial_history(self):
        """Get psychosocial history."""
        return self.patient_profile.past_medical_histories.filter(
            history_type='psychosocial',
            is_active=True
        ).first()
    
    @property
    def vitals_history(self):
        """Get all vitals from examinations."""
        vitals = []
        for consultation in self.patient_profile.consultations.all():
            for exam in consultation.examinations.filter(examination_type='vitals'):
                vitals.append({
                    'date': consultation.created_at,
                    'bp': f"{exam.bp_systolic}/{exam.bp_diastolic}" if exam.bp_systolic else None,
                    'heart_rate': exam.heart_rate,
                    'temperature': exam.temperature,
                    'weight': exam.weight,
                    'bmi': exam.bmi,
                })
        return vitals
    
    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        return f"Medical Record #{self.record_number} - {patient_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate record number if not exists
        if not self.record_number:
            self.record_number = f"MRN-{uuid.uuid4().hex[:8].upper()}-{self.patient_profile.id}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_profile', 'record_number']),
            models.Index(fields=['record_number']),
        ]


# ============================================
# HELPER FUNCTIONS
# ============================================

def create_consultation_from_appointment(appointment):
    """Create a consultation from an appointment."""
    consultation = Consultation.objects.create(
        appointment=appointment,
        patient_profile=appointment.patient_profile,
        doctor_profile=appointment.doctor_profile,
        type=appointment.type,
        clinic_location=appointment.clinic.name if appointment.clinic else '',
        status='ongoing'
    )
    return consultation


def get_patient_full_medical_record(patient_profile):
    """
    Get the complete medical record for a patient.
    This is the main entry point for viewing a patient's entire medical history.
    """
    medical_record = MedicalRecord.objects.get_or_create(patient_profile=patient_profile)[0]
    
    # Gather all data
    consultations = patient_profile.consultations.all()
    past_histories = patient_profile.past_medical_histories.filter(is_active=True)
    medications = patient_profile.prescriptions.filter(status='active')
    lab_tests = patient_profile.lab_tests.all()
    
    # Get all examinations
    examinations = []
    for consultation in consultations:
        examinations.extend(consultation.examinations.all())
    
    return {
        'medical_record': medical_record,
        'consultations': consultations,
        'past_medical_histories': past_histories,
        'medications': medications,
        'lab_tests': lab_tests,
        'examinations': examinations,
    }


# ============================================
# SIGNALS
# ============================================
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Consultation)
def update_medical_record_on_consultation(sender, instance, created, **kwargs):
    """
    When a consultation is completed, update the patient's medical record.
    """
    if instance.status == 'completed':
        # Get or create the medical record
        medical_record, _ = MedicalRecord.objects.get_or_create(
            patient_profile=instance.patient_profile
        )
        
        # Update last review date
        medical_record.last_review_date = instance.updated_at
        medical_record.last_updated_by = instance.doctor_profile
        
        # Update active problems summary from assessment
        if instance.assessment:
            if medical_record.active_problems:
                if instance.assessment not in medical_record.active_problems:
                    medical_record.active_problems += f"\n• {instance.assessment}"
            else:
                medical_record.active_problems = f"• {instance.assessment}"
        
        # Update vitals from examinations
        vitals_exam = instance.examinations.filter(examination_type='vitals').first()
        if vitals_exam:
            vitals_summary = []
            if vitals_exam.bp_systolic and vitals_exam.bp_diastolic:
                vitals_summary.append(f"BP: {vitals_exam.bp_systolic}/{vitals_exam.bp_diastolic}")
            if vitals_exam.heart_rate:
                vitals_summary.append(f"HR: {vitals_exam.heart_rate}")
            if vitals_exam.temperature:
                vitals_summary.append(f"Temp: {vitals_exam.temperature}°C")
            if vitals_exam.weight:
                vitals_summary.append(f"Weight: {vitals_exam.weight}kg")
            if vitals_exam.bmi:
                vitals_summary.append(f"BMI: {vitals_exam.bmi}")
            
            if vitals_summary:
                medical_record.vitals_summary = ", ".join(vitals_summary)
        
        medical_record.save()