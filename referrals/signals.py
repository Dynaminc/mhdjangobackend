# apps/specialists/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import SpecialistReferral


@receiver(pre_save, sender=SpecialistReferral)
def track_previous_status(sender, instance, **kwargs):
    """Store the previous status so post_save can detect changes."""
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        old = SpecialistReferral.objects.get(pk=instance.pk)
        instance._previous_status = old.status
    except SpecialistReferral.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=SpecialistReferral)
def handle_referral_email(sender, instance, created, **kwargs):
    """
    Send emails:
      - on creation        → acknowledgment to patient
      - on status change   → status update to patient
    """
    if created:
        print('Creating created ', 'handle referral')
        _send_referral_email(instance, template='referral_received')
        return

    previous = getattr(instance, '_previous_status', None)
    if previous != instance.status:
        _send_referral_email(
            instance,
            template=f'referral_{instance.status}',
        )


# =====================================================
# INTERNAL
# =====================================================
def _send_referral_email(referral, template):
    """Render and send the given email template for a referral."""
    context = {
        'referral': referral,
        'patient_name': referral.full_name,
        'reference_id': referral.reference_id,
        'status': referral.get_status_display(),
        'frontend_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
        'signup_link': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/auth?ref_id={referral.reference_id} ",
        'meeting_link': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/meet?ref_id={referral.reference_id}",
    }

    print('referral here', context)
    # Templates live in templates/emails/<name>.html and .txt
    html_template = f'emails/{template}.html'
    txt_template = f'emails/{template}.txt'

    # try:
    html_message = render_to_string(html_template, context)
    
    plain_message = strip_tags(html_message)
    # except Exception:
    #     # Fallback if templates don't exist yet
    #     print('this is an exception')
    #     plain_message = (
    #         f"Hi {referral.full_name},\n\n"
    #         f"Your referral {referral.reference_id} is now: "
    #         f"{referral.get_status_display()}.\n\n"
    #         f"— MHPro Team"
    #     )
    #     html_message = None

    subject_map = {
        'referral_received': f"We received your referral request ({referral.reference_id})",
        'referral_under_review': f"Referral {referral.reference_id} is under review",
        'referral_approved': f"Referral {referral.reference_id} approved",
        'referral_scheduled': f"Referral {referral.reference_id} scheduled",
        'referral_completed': f"Referral {referral.reference_id} completed",
        'referral_rejected': f"Referral {referral.reference_id} update",
        'referral_cancelled': f"Referral {referral.reference_id} cancelled",
    }
    print("we are seingin maile right now")
    # send_mail(
    #     subject=subject_map.get(template, f"Referral {referral.reference_id} update"),
    #     message=plain_message,
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[referral.email],
    #     html_message=html_message,
    #     fail_silently=True,
    # )