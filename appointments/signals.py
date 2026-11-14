# apps/appointments/signals.py
"""
State-tracking + validation signals for appointments and queue entries.

These do NOT create notifications. They only:
  • validate data
  • compute defaults
  • attach `_previous_*` attributes to instances so the notification
    receivers in notifications/models.py can detect real transitions
  • maintain queue ordering
  • materialise an Appointment when a QueueEntry is admitted
"""
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Appointment, QueueEntry


# ============================================
# Appointment — validation
# ============================================
@receiver(pre_save, sender=Appointment)
def validate_appointment_time(sender, instance, **kwargs):
    """End time must be after start time.

    Only validates when one of the two fields is actually changing, so a
    legacy bad row can still be updated (e.g. status change).
    """
    update_fields = kwargs.get('update_fields')
    if update_fields and not ({'start_time', 'end_time'} & set(update_fields)):
        return

    if instance.start_time and instance.end_time:
        if instance.start_time >= instance.end_time:
            raise ValidationError(
                {'end_time': 'End time must be after start time.'}
            )


@receiver(pre_save, sender=Appointment)
def set_end_time_if_not_provided(sender, instance, **kwargs):
    """Auto-compute end_time from the clinic's appointment_duration."""
    if not instance.start_time or instance.end_time:
        return

    update_fields = kwargs.get('update_fields')
    if update_fields and 'end_time' not in update_fields:
        return

    duration = instance.clinic.appointment_duration if instance.clinic else 30
    start_dt = datetime.combine(instance.appointment_date, instance.start_time)
    instance.end_time = (start_dt + timedelta(minutes=duration)).time()


# ============================================
# Appointment — capture previous state
# ============================================
@receiver(pre_save, sender=Appointment)
def track_appointment_previous_state(sender, instance, **kwargs):
    """Capture previous status + assigned doctor.

    notifications.models.handle_appointment_notification relies on:
        instance._previous_status
        instance._previous_doctor_id
    """
    if not instance.pk:
        instance._previous_status = None
        instance._previous_doctor_id = None
        return

    try:
        old = (
            sender.objects
            .only('status', 'doctor_profile_id')
            .get(pk=instance.pk)
        )
        instance._previous_status = old.status
        instance._previous_doctor_id = old.doctor_profile_id
    except sender.DoesNotExist:
        instance._previous_status = None
        instance._previous_doctor_id = None


# ============================================
# QueueEntry — capture previous state
# ============================================
@receiver(pre_save, sender=QueueEntry)
def track_queue_previous_state(sender, instance, **kwargs):
    """Capture previous queue_position and status.

    notifications.models.handle_queue_notification reads:
        instance._original_queue_position
    create_appointment_on_admit reads:
        instance._original_status
    """
    if not instance.pk:
        instance._original_queue_position = None
        instance._original_status = None
        return

    try:
        old = (
            sender.objects
            .only('queue_position', 'status')
            .get(pk=instance.pk)
        )
        instance._original_queue_position = old.queue_position
        instance._original_status = old.status
    except sender.DoesNotExist:
        instance._original_queue_position = None
        instance._original_status = None


# ============================================
# QueueEntry — recalculate positions
# ============================================
@receiver(post_save, sender=QueueEntry)
def update_queue_positions(sender, instance, created, **kwargs):
    """Recompute queue_position for all waiting entries of a doctor.

    Guarded against re-entry: when this signal saves a row with only
    queue_position in update_fields, we skip to avoid an O(n^2) loop.
    """
    update_fields = kwargs.get('update_fields') or set()
    if not created and set(update_fields) <= {'queue_position'}:
        return

    if not instance.doctor_profile_id:
        return

    with transaction.atomic():
        waiting = (
            QueueEntry.objects
            .select_for_update()
            .filter(
                status='waiting',
                doctor_profile_id=instance.doctor_profile_id,
            )
            .order_by('-priority', 'created_at')
        )

        for position, entry in enumerate(waiting, start=1):
            if entry.queue_position != position:
                # .update() avoids re-firing post_save for every row
                QueueEntry.objects.filter(pk=entry.pk).update(
                    queue_position=position,
                )


# ============================================
# QueueEntry — admit → materialise Appointment
# ============================================
@receiver(post_save, sender=QueueEntry)
def create_appointment_on_admit(sender, instance, **kwargs):
    """When a QueueEntry transitions to 'admitted', create an Appointment.

    Duplicate guard is a DB lookup (not an in-memory flag) so it survives
    instance reloads and admin re-saves.
    """
    if instance.status != 'admitted':
        return

    previous_status = getattr(instance, '_original_status', None)
    if previous_status == 'admitted':
        return

    if not instance.doctor_profile_id:
        return

    marker = f"Queue entry #{instance.id}"
    if Appointment.objects.filter(notes__contains=marker).exists():
        return

    clinic = instance.doctor_profile.clinics.first()
    now = timezone.now()

    Appointment.objects.create(
        patient_profile=instance.patient_profile,
        doctor_profile=instance.doctor_profile,
        clinic=clinic,
        appointment_date=now.date(),
        start_time=now.time(),
        status='in_progress',
        type='physical',
        reason=instance.reason,
        notes=f"{marker} - Admitted",
    )