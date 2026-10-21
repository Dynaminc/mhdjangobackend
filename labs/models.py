# apps/labs/models.py
import uuid
from django.db import models
from django.utils import timezone

from accounts.models import BaseModel, DoctorProfile, PatientProfile
from consultations.models import Consultation


class LabTestOrder(BaseModel):
    """A single lab test item ordered during a consultation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Relationships ─────────────────────────────────
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='lab_orders',
        null=True, blank=True,
    )
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='lab_orders',
    )
    doctor_profile = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='lab_orders',
    )

    # ── What to run ───────────────────────────────────
    test_name = models.CharField(
        max_length=255,
        help_text="Free text — 'CBC', 'Lipid Profile', 'Malaria Parasite'",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Free-text instructions for the lab",
    )
    clinical_indication = models.TextField(
        blank=True,
        help_text="Why the test is being ordered",
    )

    # ── Results & attachments ─────────────────────────
    result_value = models.TextField(
        blank=True,
        help_text="Result text — entered by patient or doctor",
    )
    attachment_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of file URLs (e.g. /api/v1/files/<uuid>/) attached as results",
    )

    # ✅ Doctor's interpretation / comment on the result
    doctor_comment = models.TextField(
        blank=True,
        help_text="Doctor's interpretation or comment on the result",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.test_name} — {self.patient_profile.profile.user.get_full_name()}"

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['patient_profile']),
            models.Index(fields=['doctor_profile']),
        ]