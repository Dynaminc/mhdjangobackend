from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


# ─────────────────────────────────────────────────────────────
#  1. SPECIALIST DIRECTORY
# ─────────────────────────────────────────────────────────────
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator
from django.utils import timezone


# ═════════════════════════════════════════════════════════════
#  ENUMS / CHOICES
# ═════════════════════════════════════════════════════════════
class Specialty(models.TextChoices):
    PSYCHIATRY = 'psychiatry', 'Psychiatry'
    CLINICAL_PSYCHOLOGY = 'clinical_psychology', 'Clinical Psychology'
    NEUROLOGY = 'neurology', 'Neurology'
    CARDIOLOGY = 'cardiology', 'Cardiology'
    ENDOCRINOLOGY = 'endocrinology', 'Endocrinology'
    DERMATOLOGY = 'dermatology', 'Dermatology'
    ORTHOPEDICS = 'orthopedics', 'Orthopedics'
    GASTROENTEROLOGY = 'gastroenterology', 'Gastroenterology'
    PEDIATRICS = 'pediatrics', 'Pediatrics'
    OBGYN = 'obgyn', 'Obstetrics & Gynaecology'
    ONCOLOGY = 'oncology', 'Oncology'
    RHEUMATOLOGY = 'rheumatology', 'Rheumatology'
    NEPHROLOGY = 'nephrology', 'Nephrology'
    PULMONOLOGY = 'pulmonology', 'Pulmonology'
    UROLOGY = 'urology', 'Urology'
    OPHTHALMOLOGY = 'ophthalmology', 'Ophthalmology'
    ENT = 'ent', 'ENT'
    GENERAL_SURGERY = 'general_surgery', 'General Surgery'
    FAMILY_MEDICINE = 'family_medicine', 'Family Medicine'
    OTHER = 'other', 'Other'


class AvailabilityStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    BUSY = 'busy', 'Busy'
    UNAVAILABLE = 'unavailable', 'Unavailable'
    ON_LEAVE = 'on_leave', 'On Leave'
    ACCEPTING_WAITLIST = 'accepting_waitlist', 'Accepting Waitlist'


class VerificationLevel(models.TextChoices):
    UNVERIFIED = 'unverified', 'Unverified'
    PENDING = 'pending', 'Pending Review'
    VERIFIED = 'verified', 'Verified'
    PREMIUM = 'premium', 'Premium Verified'


class ConsultationFormat(models.TextChoices):
    VIDEO = 'video', 'Video Call'
    IN_PERSON = 'in_person', 'In-Person'
    PHONE = 'phone', 'Phone Call'
    CHAT = 'chat', 'Chat'
    HYBRID = 'hybrid', 'Hybrid (Video + In-person)'


class LanguageProficiency(models.TextChoices):
    BASIC = 'basic', 'Basic'
    CONVERSATIONAL = 'conversational', 'Conversational'
    FLUENT = 'fluent', 'Fluent'
    NATIVE = 'native', 'Native'


class CredentialType(models.TextChoices):
    DEGREE = 'degree', 'Degree'
    LICENSE = 'license', 'Medical License'
    BOARD_CERT = 'board_cert', 'Board Certification'
    FELLOWSHIP = 'fellowship', 'Fellowship'
    TRAINING = 'training', 'Specialised Training'
    AWARD = 'award', 'Award / Honours'
    PUBLICATION = 'publication', 'Publication'
    MEMBERSHIP = 'membership', 'Professional Membership'


class SocialPlatform(models.TextChoices):
    LINKEDIN = 'linkedin', 'LinkedIn'
    WEBSITE = 'website', 'Personal Website'
    RESEARCHGATE = 'researchgate', 'ResearchGate'
    PUBMED = 'pubmed', 'PubMed'
    ORCID = 'orcid', 'ORCID'
    GOOGLE_SCHOLAR = 'google_scholar', 'Google Scholar'
    TWITTER = 'twitter', 'Twitter / X'
    YOUTUBE = 'youtube', 'YouTube'
    INSTAGRAM = 'instagram', 'Instagram'
    FACEBOOK = 'facebook', 'Facebook'
    OTHER = 'other', 'Other'


class Gender(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    OTHER = 'other', 'Other'
    PREFER_NOT = 'prefer_not', 'Prefer Not To Say'


# ═════════════════════════════════════════════════════════════
#  1. SPECIALIST (main model)
# ═════════════════════════════════════════════════════════════
class Specialist(models.Model):
    """
    A specialist that patients can be referred to.
    Holds all identity, bio, stats, contact, and profile display fields.
    """

    # ─── IDENTITY ─────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    # ─── CORE NAME & TITLE ────────────────────────────────
    title = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. Dr., Prof., Mr., Ms."
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    preferred_name = models.CharField(
        max_length=100, blank=True,
        help_text="How the specialist prefers to be addressed"
    )
    pronouns = models.CharField(
        max_length=30, blank=True,
        help_text="e.g. she/her, he/him, they/them"
    )
    gender = models.CharField(
        max_length=20, choices=Gender.choices,
        blank=True
    )

    # ─── CREDENTIALS (displayed as small badge) ───────────
    credentials = models.CharField(
        max_length=200, blank=True,
        help_text="e.g. MBBS, MRCPsych, PhD — shown next to name"
    )

    # ─── PROFESSIONAL IDENTITY ────────────────────────────
    specialty = models.CharField(max_length=50, choices=Specialty.choices)
    sub_specialties = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated sub-specialties shown on the specialty line"
    )
    headline = models.CharField(
        max_length=200, blank=True,
        help_text="One-line professional headline, e.g. 'Trauma-informed Psychiatrist'"
    )

    # ─── SHORT & LONG BIO ─────────────────────────────────
    short_bio = models.CharField(
        max_length=300,
        help_text="2–3 line preview shown on the card (max 300 chars)"
    )
    long_bio = models.TextField(
        blank=True,
        help_text="Full multi-paragraph biography for the profile page"
    )
    personal_philosophy = models.TextField(
        blank=True,
        help_text="A quote or statement about their approach to care"
    )

    # ─── AVATAR / MEDIA ───────────────────────────────────
    avatar = models.ImageField(
        upload_to='specialists/avatars/',
        null=True, blank=True,
        help_text="Profile photo (used as rounded square in the card)"
    )
    avatar_url = models.URLField(
        blank=True,
        help_text="External avatar URL (fallback if no upload)"
    )
    cover_image = models.ImageField(
        upload_to='specialists/covers/',
        null=True, blank=True,
        help_text="Optional cover image for the full profile header"
    )
    video_intro_url = models.URLField(
        blank=True,
        help_text="Optional short intro video link"
    )

    # ─── LOCATION ─────────────────────────────────────────
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. Africa/Lagos"
    )
    is_remote = models.BooleanField(
        default=False,
        help_text="True if the specialist primarily offers remote consultations"
    )

    # ─── EXPERIENCE ───────────────────────────────────────
    years_experience = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        default=0
    )
    years_in_practice_start = models.DateField(
        null=True, blank=True,
        help_text="Year they began practising (used to auto-compute experience)"
    )
    total_consultations = models.PositiveIntegerField(
        default=0,
        help_text="Total lifetime consultations (shown as a stat)"
    )

    # ─── LANGUAGES (can be overridden by SpecialistLanguage) ─
    languages = models.CharField(
        max_length=200, blank=True,
        help_text="Comma-separated list, e.g. 'English, Yoruba, French'"
    )

    # ─── CONSULTATION DETAILS ─────────────────────────────
    consultation_formats = models.JSONField(
        default=list, blank=True,
        help_text="List of formats offered, e.g. ['video', 'in_person']"
    )
    session_length_minutes = models.PositiveSmallIntegerField(
        default=45,
        help_text="Default session length in minutes"
    )
    session_length_max_minutes = models.PositiveSmallIntegerField(
        default=60, null=True, blank=True,
        help_text="Upper bound if sessions vary"
    )
    response_time_hours = models.PositiveSmallIntegerField(
        default=24,
        help_text="Typical response time to patient messages (in hours)"
    )
    follow_up_included = models.BooleanField(
        default=True,
        help_text="Whether a follow-up session is included"
    )

    # ─── FEES (optional, internal only) ───────────────────
    consultation_fee_min = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    consultation_fee_max = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='NGN')
    accepts_insurance = models.BooleanField(default=False)
    insurance_providers = models.JSONField(
        default=list, blank=True,
        help_text="List of accepted insurance providers"
    )

    # ─── STATS (rating/reviews — can be computed) ─────────
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average rating 0.00–5.00"
    )
    total_reviews = models.PositiveIntegerField(default=0)
    response_rate_percent = models.PositiveSmallIntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Message response rate, shown as a percentage"
    )
    recommendation_rate = models.PositiveSmallIntegerField(
        default=100, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # ─── TAGS (quick chips) ───────────────────────────────
    tags = models.JSONField(
        default=list, blank=True,
        help_text="Short labels shown as chips on the card, e.g. ['CBT','Trauma']"
    )
    areas_of_expertise = models.JSONField(
        default=list, blank=True,
        help_text="Longer list of conditions/specialties for the full profile"
    )

    # ─── STATUS & VERIFICATION ────────────────────────────
    status = models.CharField(
        max_length=25, choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE
    )
    is_online_now = models.BooleanField(
        default=False,
        help_text="Real-time flag for the green online dot"
    )
    verification_level = models.CharField(
        max_length=20, choices=VerificationLevel.choices,
        default=VerificationLevel.UNVERIFIED
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If False, the card is hidden from the directory"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured specialists appear at the top of the directory"
    )

    # ─── LINKED USER (optional) ───────────────────────────
    user = models.OneToOneField(
        'accounts.Profile', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='specialist_profile',
        help_text="If the specialist also has a login on the platform"
    )

    # ─── INTERNAL NOTES ───────────────────────────────────
    internal_notes = models.TextField(
        blank=True,
        help_text="Private notes for admins — never shown to patients"
    )

    # ─── TIMESTAMPS ───────────────────────────────────────
    joined_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-is_featured', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['status', '-is_featured']),
            models.Index(fields=['specialty']),
            models.Index(fields=['country']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Specialist'
        verbose_name_plural = 'Specialists'

    def __str__(self):
        return f"{self.title} {self.first_name} {self.last_name}".strip()

    # ─── PROPERTIES USED BY THE FRONTEND ──────────────────
    @property
    def full_name(self):
        parts = [self.title, self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)

    @property
    def display_name(self):
        """Preferred name if set, otherwise first name."""
        return self.preferred_name or self.first_name

    @property
    def avatar_display(self):
        """Return the best avatar URL, or None."""
        if self.avatar:
            return self.avatar.url
        return self.avatar_url or None

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def is_available_now(self):
        return self.status == AvailabilityStatus.AVAILABLE

    @property
    def is_verified(self):
        return self.verification_level in (
            VerificationLevel.VERIFIED,
            VerificationLevel.PREMIUM,
        )

    def save(self, *args, **kwargs):
        # Auto-generate slug
        if not self.slug:
            base = f"{self.first_name}-{self.last_name}".lower().replace(" ", "-")
            base = "".join(c for c in base if c.isalnum() or c == "-")
            slug = base
            n = 1
            while Specialist.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


# ═════════════════════════════════════════════════════════════
#  2. PROFESSIONAL TIMELINE (for the timeline section)
# ═════════════════════════════════════════════════════════════
class SpecialistTimeline(models.Model):
    """
    A single entry in the specialist's professional history timeline.
    e.g. '2020 — Present · Consultant Psychiatrist · Marvell Health'
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    specialist = models.ForeignKey(
        Specialist, on_delete=models.CASCADE, related_name='timeline'
    )

    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Leave blank if this is the current role"
    )
    is_current = models.BooleanField(
        default=False,
        help_text="Marks the item with a filled dot in the timeline"
    )

    title = models.CharField(
        max_length=200,
        help_text="e.g. 'Consultant Psychiatrist'"
    )
    organization = models.CharField(
        max_length=200,
        help_text="e.g. 'Marvell Health'"
    )
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(
        blank=True,
        help_text="1–2 sentence summary of responsibilities"
    )

    display_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers appear first"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-start_year']
        verbose_name = 'Timeline Entry'
        verbose_name_plural = 'Timeline Entries'

    def __str__(self):
        end = self.end_year or 'Present'
        return f"{self.start_year}–{end} · {self.title} · {self.organization}"

    @property
    def year_range(self):
        end = self.end_year or 'Present'
        return f"{self.start_year} — {end}"


# ═════════════════════════════════════════════════════════════
#  3. CREDENTIALS (degrees, licenses, certifications)
# ═════════════════════════════════════════════════════════════
class SpecialistCredential(models.Model):
    """
    e.g. 'MBBS — University of Lagos, 2013'
         'MRCPsych — Royal College of Psychiatrists, 2018'
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    specialist = models.ForeignKey(
        Specialist, on_delete=models.CASCADE, related_name='credentials_list'
    )

    credential_type = models.CharField(
        max_length=30, choices=CredentialType.choices,
        default=CredentialType.DEGREE
    )
    title = models.CharField(
        max_length=200,
        help_text="e.g. 'MBBS', 'MRCPsych', 'CBT Practitioner'"
    )
    institution = models.CharField(
        max_length=200, blank=True,
        help_text="e.g. 'University of Lagos', 'Beck Institute'"
    )
    year_obtained = models.PositiveSmallIntegerField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(
        max_length=100, blank=True,
        help_text="For licenses only — kept internal"
    )
    verification_url = models.URLField(
        blank=True,
        help_text="Link to verify the credential with the issuing body"
    )
    is_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-year_obtained']
        verbose_name = 'Credential'
        verbose_name_plural = 'Credentials'

    def __str__(self):
        parts = [self.title]
        if self.institution:
            parts.append(self.institution)
        if self.year_obtained:
            parts.append(str(self.year_obtained))
        return " — ".join(parts)


# ═════════════════════════════════════════════════════════════
#  4. LANGUAGES (per-specialist, with proficiency)
# ═════════════════════════════════════════════════════════════
class SpecialistLanguage(models.Model):
    """
    Structured languages for filtering and display.
    e.g. English (Fluent), Yoruba (Native)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    specialist = models.ForeignKey(
        Specialist, on_delete=models.CASCADE, related_name='languages_list'
    )
    language = models.CharField(max_length=100)
    proficiency = models.CharField(
        max_length=20, choices=LanguageProficiency.choices,
        default=LanguageProficiency.FLUENT
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'language']
        unique_together = ('specialist', 'language')
        verbose_name = 'Language'
        verbose_name_plural = 'Languages'

    def __str__(self):
        return f"{self.language} ({self.get_proficiency_display()})"


# ═════════════════════════════════════════════════════════════
#  5. SOCIAL LINKS
# ═════════════════════════════════════════════════════════════
class SpecialistSocialLink(models.Model):
    """
    LinkedIn, personal website, ResearchGate, PubMed, etc.
    NO email / phone ever stored here — those are internal-only.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    specialist = models.ForeignKey(
        Specialist, on_delete=models.CASCADE, related_name='social_links'
    )
    platform = models.CharField(
        max_length=30, choices=SocialPlatform.choices
    )
    url = models.URLField(validators=[URLValidator()])
    label = models.CharField(
        max_length=100, blank=True,
        help_text="Optional custom label, e.g. 'My research site'"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="If False, link is hidden from the public card"
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'platform']
        unique_together = ('specialist', 'platform', 'url')
        verbose_name = 'Social Link'
        verbose_name_plural = 'Social Links'

    def __str__(self):
        return f"{self.get_platform_display()} → {self.url}"


# ═════════════════════════════════════════════════════════════
#  6. TAGS (structured — for filtering & chips)
# ═════════════════════════════════════════════════════════════
class SpecialistTag(models.Model):
    """
    e.g. 'Depression', 'Anxiety', 'CBT', 'Trauma'
    Chip on the card, filterable in the directory.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    specialist = models.ForeignKey(
        Specialist, on_delete=models.CASCADE, related_name='tag_list'
    )
    name = models.CharField(max_length=100)
    color = models.CharField(
        max_length=20, default='default',
        choices=[
            ('default', 'Green (default)'),
            ('soft', 'Sage (soft)'),
            ('info', 'Blue (info)'),
            ('warning', 'Orange'),
            ('danger', 'Red'),
        ],
        help_text="Visual style of the chip"
    )
    category = models.CharField(
        max_length=30, blank=True,
        help_text="Optional grouping, e.g. 'condition' or 'modality'"
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        unique_together = ('specialist', 'name')
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


# ═════════════════════════════════════════════════════════════
#  7. AVAILABILITY WEEK (for the mini-calendar on the card)
# ═════════════════════════════════════════════════════════════
class SpecialistWeeklyAvailability(models.Model):
    """
    Simple weekly snapshot shown on the card's full profile.
    For real booking, use AppointmentSlot (separate model).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    specialist = models.ForeignKey(
        Specialist, on_delete=models.CASCADE, related_name='weekly_availability'
    )
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    slots_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of free slots on this day (for informational display)"
    )
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['date']
        unique_together = ('specialist', 'date')
        verbose_name = 'Weekly Availability'
        verbose_name_plural = 'Weekly Availability'

    def __str__(self):
        return f"{self.specialist} · {self.date} · {'open' if self.is_available else 'booked'}"


# ═════════════════════════════════════════════════════════════
#  8. REVIEWS (for the stats row)
# ═════════════════════════════════════════════════════════════
class SpecialistReview(models.Model):
    """
    Patient reviews that feed into average_rating / total_reviews.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    specialist = models.ForeignKey(
        Specialist, on_delete=models.CASCADE, related_name='reviews'
    )
    reviewer = models.ForeignKey(
        'accounts.Profile', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='specialist_reviews'
    )
    reviewer_display_name = models.CharField(
        max_length=100, blank=True,
        help_text="Shown on the card; can be anonymised, e.g. 'A. O.'"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def __str__(self):
        return f"{self.rating}★ — {self.specialist}"
    
# ─────────────────────────────────────────────────────────────
#  2. SPECIALIST REFERRAL REQUEST (the main intake)
# ─────────────────────────────────────────────────────────────
class SpecialistReferral(models.Model):
    """
    The main referral request submitted from the patient form.
    Holds all personal, complaint, and consent data.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not', 'Prefer not to say'),
    ]

    MARITAL_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
    ]

    DURATION_CHOICES = [
        ('less_than_week', 'Less than a week'),
        ('1_4_weeks', '1–4 weeks'),
        ('1_6_months', '1–6 months'),
        ('6_12_months', '6–12 months'),
        ('over_year', 'Over a year'),
    ]

    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ]

    FREQUENCY_CHOICES = [
        ('constant', 'Constant'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('occasional', 'Occasional'),
    ]

    # Reference
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_id = models.CharField(max_length=30, unique=True, db_index=True)

    # Personal info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField()
    sex = models.CharField(max_length=20, choices=SEX_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_CHOICES, blank=True)
    religion = models.CharField(max_length=100, blank=True)
    tribe = models.CharField(max_length=100, blank=True)

    # Contact & location
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30)
    email = models.EmailField()

    # Complaint
    complaint = models.TextField()
    symptoms = models.TextField(blank=True)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, blank=True)
    progression = models.TextField()
    expectations = models.TextField()

    # Consent
    consented_at = models.DateTimeField(null=True, blank=True)
    consent_version = models.CharField(max_length=20, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Assignment
    assigned_specialist = models.ForeignKey(
        Specialist, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='referrals'
    )

    # Review
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_referrals'
    )
    review_notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    linked_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='linked_referral',
        help_text="The user account created from this referral",
    )
    linked_at = models.DateTimeField(null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)

    # apps/specialists/models.py — add to SpecialistReferral

    meeting_link = models.URLField(blank=True, null=True)
    appointment_date = models.DateField(null=True, blank=True)
    appointment_time = models.TimeField(null=True, blank=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.reference_id} — {self.first_name} {self.last_name} ({self.status})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = self._generate_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference():
        return "REF-" + uuid.uuid4().hex[:10].upper()