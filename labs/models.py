# apps/labs/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import BaseModel, Profile, DoctorProfile, PatientProfile
from consultations.models import MedicalRecord, Consultation
import uuid
from django.utils import timezone


# ============================================
# LAB TEST CATALOG - Master list of available tests
# ============================================
class LabTestCatalog(BaseModel):
    """Master catalog of all available lab tests"""
    
    CATEGORY_CHOICES = (
        ('hematology', 'Hematology'),
        ('chemistry', 'Chemistry'),
        ('microbiology', 'Microbiology'),
        ('immunology', 'Immunology'),
        ('pathology', 'Pathology'),
        ('radiology', 'Radiology'),
        ('cardiology', 'Cardiology'),
        ('endocrinology', 'Endocrinology'),
        ('toxicology', 'Toxicology'),
        ('genetics', 'Genetics'),
        ('other', 'Other'),
    )
    
    SAMPLE_TYPE_CHOICES = (
        ('blood', 'Blood'),
        ('urine', 'Urine'),
        ('stool', 'Stool'),
        ('sputum', 'Sputum'),
        ('csf', 'Cerebrospinal Fluid'),
        ('tissue', 'Tissue'),
        ('swab', 'Swab'),
        ('saliva', 'Saliva'),
        ('other', 'Other'),
    )
    
    # Basic info
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique test code (e.g., CBC-001)"
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Full test name"
    )
    short_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Short/abbreviated name"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        db_index=True,
        help_text="Test category"
    )
    
    # Sample requirements
    sample_type = models.CharField(
        max_length=20,
        choices=SAMPLE_TYPE_CHOICES,
        default='blood',
        help_text="Type of sample required"
    )
    sample_volume = models.CharField(
        max_length=50,
        blank=True,
        help_text="Required sample volume (e.g., '5 mL')"
    )
    sample_container = models.CharField(
        max_length=100,
        blank=True,
        help_text="Container type (e.g., 'EDTA tube')"
    )
    fasting_required = models.BooleanField(
        default=False,
        help_text="Whether fasting is required"
    )
    fasting_hours = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of hours fasting required"
    )
    
    # Reference ranges
    reference_range_male = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference range for males"
    )
    reference_range_female = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference range for females"
    )
    reference_range_child = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference range for children"
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unit of measurement"
    )
    
    # Cost and time
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Cost of the test"
    )
    turnaround_time_hours = models.IntegerField(
        default=24,
        help_text="Expected turnaround time in hours"
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this test is currently available"
    )
    requires_authorization = models.BooleanField(
        default=False,
        help_text="Whether special authorization is required"
    )
    requires_consent = models.BooleanField(
        default=False,
        help_text="Whether patient consent is required"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the test"
    )
    clinical_indications = models.TextField(
        blank=True,
        help_text="Clinical indications for ordering this test"
    )
    interpretation_notes = models.TextField(
        blank=True,
        help_text="Notes on how to interpret results"
    )
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_reference_range(self, gender='female', age=None):
        """Get appropriate reference range based on patient demographics"""
        if age and age < 18:
            return self.reference_range_child
        if gender == 'male':
            return self.reference_range_male
        return self.reference_range_female
    
    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['code', 'category']),
            models.Index(fields=['name', 'category']),
            models.Index(fields=['is_active']),
        ]

# apps/labs/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from accounts.models import BaseModel, DoctorProfile, PatientProfile


class LabTestOrder(BaseModel):
    """Lab test order placed by a doctor"""

    PRIORITY_CHOICES = (
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
    )

    STATUS_CHOICES = (
        ('ordered', 'Ordered'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    # -------------------------------------------------
    # Identifiers
    # -------------------------------------------------
    order_number = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text="Auto-generated (e.g., LAB-2026-0001)"
    )
    patient_profile = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE,
        related_name='lab_orders'
    )
    doctor_profile = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE,
        related_name='lab_orders'
    )

    # -------------------------------------------------
    # Test details — free-form name, no catalog FK
    # -------------------------------------------------
    test_name = models.CharField(max_length=255)
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='routine'
    )

    clinical_notes = models.TextField(blank=True)
    clinical_indication = models.TextField(blank=True)

    # -------------------------------------------------
    # Status & dates
    # -------------------------------------------------
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='ordered', db_index=True
    )
    ordered_date = models.DateTimeField(auto_now_add=True)
    collected_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    cancelled_date = models.DateTimeField(null=True, blank=True)

    # -------------------------------------------------
    # Results
    # -------------------------------------------------
    result_value = models.CharField(max_length=255, blank=True)
    result_notes = models.TextField(blank=True)
    is_abnormal = models.BooleanField(default=False)

    # -------------------------------------------------
    # Auto-numbering
    # -------------------------------------------------
    def save(self, *args, **kwargs):
        if not self.order_number:
            year = timezone.now().year
            count = LabTestOrder.objects.filter(
                created_at__year=year
            ).count() + 1
            self.order_number = f"LAB-{year}-{str(count).zfill(4)}"
        super().save(*args, **kwargs)

    # -------------------------------------------------
    # Status helpers
    # -------------------------------------------------
    def cancel(self):
        self.status = 'cancelled'
        self.cancelled_date = timezone.now()
        self.save()

    def complete(self):
        self.status = 'completed'
        self.completed_date = timezone.now()
        self.save()

    @property
    def is_completed(self):
        return self.status == 'completed'

    @property
    def is_active(self):
        return self.status in ['ordered', 'in_progress']

    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        return f"{self.order_number} - {self.test_name} - {patient_name}"

    class Meta:
        ordering = ['-ordered_date']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['patient_profile', 'status']),
            models.Index(fields=['doctor_profile', 'status']),
            models.Index(fields=['ordered_date']),
        ]
        
# ============================================
# LAB TEST ORDER
# # ============================================
# class LabTestOrder(BaseModel):
#     """Lab test order placed by a doctor"""
    
#     PRIORITY_CHOICES = (
#         ('routine', 'Routine'),
#         ('urgent', 'Urgent'),
#         ('stat', 'STAT'),
#     )
    
#     STATUS_CHOICES = (
#         ('draft', 'Draft'),
#         ('ordered', 'Ordered'),
#         ('pending', 'Pending'),
#         ('in_progress', 'In Progress'),
#         ('completed', 'Completed'),
#         ('cancelled', 'Cancelled'),
#         ('rejected', 'Rejected'),
#     )
    
#     # Relationships
#     order_number = models.CharField(
#         max_length=50,
#         unique=True,
#         db_index=True,
#         help_text="Unique order number (e.g., LAB-2026-001)"
#     )
    
#     consultation = models.ForeignKey(
#         Consultation,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='lab_orders',
#         help_text="The consultation this order belongs to"
#     )
    
#     medical_record = models.ForeignKey(
#         MedicalRecord,
#         on_delete=models.CASCADE,
#         related_name='lab_orders',
#         help_text="The patient's medical record"
#     )
    
#     patient_profile = models.ForeignKey(
#         PatientProfile,
#         on_delete=models.CASCADE,
#         related_name='lab_orders',
#         help_text="The patient this order is for"
#     )
    
#     doctor_profile = models.ForeignKey(
#         DoctorProfile,
#         on_delete=models.CASCADE,
#         related_name='lab_orders',
#         help_text="The doctor who ordered the test"
#     )
    
#     # Test details
#     test_catalog = models.ForeignKey(
#         LabTestCatalog,
#         on_delete=models.PROTECT,
#         related_name='orders',
#         help_text="The test being ordered"
#     )
    
#     # Order details
#     priority = models.CharField(
#         max_length=20,
#         choices=PRIORITY_CHOICES,
#         default='routine',
#         help_text="Order priority"
#     )
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default='ordered',
#         db_index=True,
#         help_text="Current status of the order"
#     )
    
#     ordered_date = models.DateTimeField(
#         auto_now_add=True,
#         help_text="Date the order was placed"
#     )
#     collected_date = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Date the sample was collected"
#     )
#     completed_date = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Date the test was completed"
#     )
#     cancelled_date = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Date the order was cancelled"
#     )
    
#     # Collection instructions
#     collection_instructions = models.TextField(
#         blank=True,
#         help_text="Instructions for sample collection"
#     )
#     collection_location = models.CharField(
#         max_length=255,
#         blank=True,
#         help_text="Where the sample should be collected"
#     )
    
#     # Clinical details
#     clinical_notes = models.TextField(
#         blank=True,
#         help_text="Clinical notes or indication for the test"
#     )
#     clinical_indication = models.TextField(
#         blank=True,
#         help_text="Clinical indication for ordering"
#     )
    
#     # Authorization
#     authorized_by = models.ForeignKey(
#         DoctorProfile,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='authorized_orders',
#         help_text="Doctor who authorized this order"
#     )
#     authorized_at = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Date the order was authorized"
#     )
    
#     # Consent
#     consent_obtained = models.BooleanField(
#         default=False,
#         help_text="Whether patient consent was obtained"
#     )
#     consent_obtained_at = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Date consent was obtained"
#     )
    
#     def __str__(self):
#         patient_name = self.patient_profile.profile.user.get_full_name()
#         return f"{self.order_number} - {self.test_catalog.name} - {patient_name}"
    
#     def save(self, *args, **kwargs):
#         # Auto-generate order number if not exists
#         if not self.order_number:
#             year = timezone.now().year
#             count = LabTestOrder.objects.filter(
#                 created_at__year=year
#             ).count() + 1
#             self.order_number = f"LAB-{year}-{str(count).zfill(4)}"
#         super().save(*args, **kwargs)
    
#     def cancel(self, reason=''):
#         """Cancel the order"""
#         self.status = 'cancelled'
#         self.cancelled_date = timezone.now()
#         self.save()
    
#     def complete(self):
#         """Mark the order as completed"""
#         self.status = 'completed'
#         self.completed_date = timezone.now()
#         self.save()
    
#     @property
#     def is_completed(self):
#         return self.status == 'completed'
    
#     @property
#     def is_cancelled(self):
#         return self.status == 'cancelled'
    
#     @property
#     def is_pending(self):
#         return self.status in ['ordered', 'pending']
    
#     class Meta:
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['order_number']),
#             models.Index(fields=['patient_profile', 'status']),
#             models.Index(fields=['doctor_profile', 'status']),
#             models.Index(fields=['test_catalog', 'status']),
#             models.Index(fields=['consultation']),
#             models.Index(fields=['ordered_date']),
#         ]


# ============================================
# LAB TEST RESULT
# ============================================
class LabTestResult(BaseModel):
    """Results of a completed lab test"""
    
    RESULT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('corrected', 'Corrected'),
        ('invalid', 'Invalid'),
    )
    
    # Relationship to order
    order = models.ForeignKey(
        LabTestOrder,
        on_delete=models.CASCADE,
        related_name='results',
        help_text="The order this result belongs to"
    )
    
    # Result values
    result_value = models.CharField(
        max_length=100,
        blank=True,
        help_text="The result value"
    )
    result_numeric = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Numeric result value (for sorting/charting)"
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unit of measurement"
    )
    reference_range = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference range for this result"
    )
    is_abnormal = models.BooleanField(
        default=False,
        help_text="Whether the result is abnormal"
    )
    is_critical = models.BooleanField(
        default=False,
        help_text="Whether the result is critical"
    )
    is_high = models.BooleanField(
        default=False,
        help_text="Whether the result is above normal range"
    )
    is_low = models.BooleanField(
        default=False,
        help_text="Whether the result is below normal range"
    )
    
    # Text result (for microbiology, pathology, etc.)
    result_text = models.TextField(
        blank=True,
        help_text="Text result for qualitative tests"
    )
    
    # Interpretation
    interpretation = models.TextField(
        blank=True,
        help_text="Interpretation of the result"
    )
    
    # Quality
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the result has been verified"
    )
    verified_by = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_results',
        help_text="Doctor who verified the result"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date the result was verified"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=RESULT_STATUS_CHOICES,
        default='pending',
        help_text="Status of the result"
    )
    
    # Metadata
    comments = models.TextField(
        blank=True,
        help_text="Additional comments"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date the result was reviewed"
    )
    reviewed_by = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_results',
        help_text="Doctor who reviewed the result"
    )
    
    def __str__(self):
        return f"Result for {self.order.order_number} - {self.result_value}"
    
    def verify(self, doctor):
        """Verify the result"""
        self.is_verified = True
        self.verified_by = doctor
        self.verified_at = timezone.now()
        self.status = 'verified'
        self.save()
    
    def mark_abnormal(self):
        """Mark result as abnormal"""
        self.is_abnormal = True
        self.save()
    
    def mark_normal(self):
        """Mark result as normal"""
        self.is_abnormal = False
        self.is_high = False
        self.is_low = False
        self.save()
    
    def get_status_display(self):
        return dict(self.RESULT_STATUS_CHOICES).get(self.status, self.status)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'is_abnormal']),
            models.Index(fields=['is_critical']),
            models.Index(fields=['verified_at']),
        ]


# ============================================
# LAB TEST ATTACHMENT
# ============================================
class LabTestAttachment(BaseModel):
    """Attachments for lab test results (PDF, images, etc.)"""
    
    result = models.ForeignKey(
        LabTestResult,
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text="The result this attachment belongs to"
    )
    
    file = models.FileField(
        upload_to='lab_results/%Y/%m/%d/',
        help_text="The attached file"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Original file name"
    )
    file_size = models.IntegerField(
        help_text="File size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the file"
    )
    
    uploaded_by = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lab_attachments',
        help_text="Doctor who uploaded the attachment"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the attachment"
    )
    
    def __str__(self):
        return f"{self.file_name} - {self.result.order.order_number}"


# ============================================
# LAB TEST PANEL (Group of tests)
# ============================================
class LabPanel(BaseModel):
    """A pre-defined panel of tests (e.g., Complete Metabolic Panel)"""
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the panel"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Panel code"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the panel"
    )
    tests = models.ManyToManyField(
        LabTestCatalog,
        related_name='panels',
        help_text="Tests included in this panel"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this panel is available"
    )
    
    def __str__(self):
        return f"{self.code} - {self.name}"


# ============================================
# LAB TEST PROFILE (Patient's test history)
# ============================================
class LabTestProfile(BaseModel):
    """Patient-specific lab test profile for trending"""
    
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='lab_profiles',
        help_text="The patient this profile belongs to"
    )
    
    test = models.ForeignKey(
        LabTestCatalog,
        on_delete=models.CASCADE,
        related_name='patient_profiles',
        help_text="The test this profile tracks"
    )
    
    # Trending
    last_value = models.CharField(
        max_length=100,
        blank=True,
        help_text="Most recent value"
    )
    last_value_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of most recent value"
    )
    trend = models.CharField(
        max_length=20,
        blank=True,
        choices=(
            ('stable', 'Stable'),
            ('increasing', 'Increasing'),
            ('decreasing', 'Decreasing'),
            ('fluctuating', 'Fluctuating'),
        ),
        help_text="Trend direction"
    )
    
    # Baseline
    baseline_value = models.CharField(
        max_length=100,
        blank=True,
        help_text="Baseline value for this patient"
    )
    baseline_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of baseline value"
    )
    
    # Alerts
    alert_threshold_high = models.CharField(
        max_length=50,
        blank=True,
        help_text="High threshold for alert"
    )
    alert_threshold_low = models.CharField(
        max_length=50,
        blank=True,
        help_text="Low threshold for alert"
    )
    
    def __str__(self):
        patient_name = self.patient_profile.profile.user.get_full_name()
        return f"{patient_name} - {self.test.name}"
    
    def update_trend(self, new_value):
        """Update trend based on new value"""
        if self.last_value and new_value:
            # Simple trend calculation
            try:
                old_num = float(self.last_value)
                new_num = float(new_value)
                diff_percent = ((new_num - old_num) / old_num) * 100
                
                if abs(diff_percent) < 5:
                    self.trend = 'stable'
                elif diff_percent > 5:
                    self.trend = 'increasing'
                elif diff_percent < -5:
                    self.trend = 'decreasing'
            except (ValueError, TypeError):
                pass
        
        self.last_value = new_value
        self.last_value_date = timezone.now()
        self.save()
    
    class Meta:
        unique_together = ['patient_profile', 'test']
        indexes = [
            models.Index(fields=['patient_profile', 'test']),
        ]


# ============================================
# LAB ORDER TEMPLATE (Common order sets)
# ============================================
class LabOrderTemplate(BaseModel):
    """Pre-defined order templates for common scenarios"""
    
    name = models.CharField(
        max_length=255,
        help_text="Template name"
    )
    description = models.TextField(
        blank=True,
        help_text="Template description"
    )
    tests = models.ManyToManyField(
        LabTestCatalog,
        related_name='templates',
        help_text="Tests included in this template"
    )
    created_by = models.ForeignKey(
        DoctorProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lab_templates',
        help_text="Doctor who created this template"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this template is available to all doctors"
    )
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been used"
    )
    
    def __str__(self):
        return self.name


# ============================================
# SIGNALS
# ============================================
from django.db.models.signals import post_save
from django.dispatch import receiver

# @receiver(post_save, sender=LabTestResult)
# def update_medical_record_on_lab_result(sender, instance, created, **kwargs):
#     """Update medical record when a lab result is added"""
#     if instance.is_verified and instance.is_abnormal:
#         medical_record = instance.order.medical_record
#         # Add to active problems or flag for review
#         if medical_record:
#             # Update medical record with abnormal result
#             if not medical_record.active_problems:
#                 medical_record.active_problems = ""
#             medical_record.active_problems += f"\n• Abnormal lab: {instance.order.test_catalog.name} - {instance.result_value} ({instance.reference_range})"
#             medical_record.save()


# @receiver(post_save, sender=LabTestOrder)
# def create_profile_on_first_order(sender, instance, created, **kwargs):
#     """Create lab profile for patient on first order"""
#     if created:
#         LabTestProfile.objects.get_or_create(
#             patient_profile=instance.patient_profile,
#             test=instance.test_catalog
#         )