# apps/appointments/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Appointment, QueueEntry


@receiver(pre_save, sender=Appointment)
def validate_appointment_time(sender, instance, **kwargs):
    """Validate that start_time is before end_time"""
    if instance.start_time and instance.end_time:
        if instance.start_time >= instance.end_time:
            raise ValueError("Start time must be before end time")


@receiver(pre_save, sender=Appointment)
def set_end_time_if_not_provided(sender, instance, **kwargs):
    """Auto-calculate end_time if not provided"""
    if instance.start_time and not instance.end_time:
        # Use clinic's appointment duration
        duration = instance.clinic.appointment_duration if instance.clinic else 30
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(instance.appointment_date, instance.start_time)
        end_datetime = start_datetime + timedelta(minutes=duration)
        instance.end_time = end_datetime.time()


@receiver(post_save, sender=QueueEntry)
def update_queue_positions(sender, instance, created, **kwargs):
    """Update queue positions when a new entry is added or status changes"""
    from django.db import transaction
    
    if created or instance.status in ['waiting']:
        # Recalculate queue positions for all waiting entries
        with transaction.atomic():
            waiting_entries = QueueEntry.objects.filter(
                status='waiting',
                doctor_profile=instance.doctor_profile
            ).exclude(id=instance.id).order_by('-priority', 'created_at')
            
            position = 1
            for entry in waiting_entries:
                if entry.queue_position != position:
                    entry.queue_position = position
                    entry.save(update_fields=['queue_position'])
                position += 1
            
            # Set position for new entry if waiting
            if instance.status == 'waiting':
                instance.queue_position = position
                instance.save(update_fields=['queue_position'])


@receiver(post_save, sender=QueueEntry)
def create_appointment_on_admit(sender, instance, **kwargs):
    """Create an appointment when a queue entry is admitted"""
    if instance.status == 'admitted' and not hasattr(instance, '_appointment_created'):
        # Create appointment from queue entry
        appointment = Appointment.objects.create(
            patient_profile=instance.patient_profile,
            doctor_profile=instance.doctor_profile,
            clinic=instance.doctor_profile.clinics.first(),
            appointment_date=timezone.now().date(),
            start_time=timezone.now().time(),
            status='in_progress',
            type='physical',
            reason=instance.reason,
            notes=f"Queue entry #{instance.id} - Admitted"
        )
        # Mark that appointment was created to prevent duplicate
        instance._appointment_created = True