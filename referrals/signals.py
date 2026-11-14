# apps/specialists/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
from django.db.models import Q

from notifications.models import NotificationSignalHandler

User = get_user_model()


from .models import SpecialistReferral



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
    send_mail(
        subject=subject_map.get(template, f"Referral {referral.reference_id} update"),
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[referral.email, 'info@marvellehealth.com'],
        html_message=html_message,
        fail_silently=True,
    )
    
    


def _referral_admin_recipients():
    """
    Everyone who should be told a referral needs attention.
    Covers both Profile.role='admin' AND raw Django staff/superuser accounts.
    """
    return (
        User.objects
        .filter(Q(profile__role='admin') | Q(is_staff=True) | Q(is_superuser=True))
        .distinct()
    )


def _referral_doctor_recipients(referral):
    """
    Whoever the referral is currently assigned to.
    Adapt this to the actual field name on SpecialistReferral:
      - referral.doctor_profile (FK to DoctorProfile)
      - referral.assigned_doctor (FK to User)
      - referral.doctor (FK to User)

    Returns an iterable of User objects (possibly empty).
    """
    doctor_profile = getattr(referral, 'doctor_profile', None)
    if doctor_profile is not None:
        return [doctor_profile.profile.user]

    assigned = getattr(referral, 'assigned_doctor', None) or getattr(referral, 'doctor', None)
    if assigned is not None:
        # Support either User or DoctorProfile here
        return [getattr(assigned, 'profile', assigned)]

    return []


def _create_referral_notifications(referral, event, *, notify_admins=True, notify_doctors=True):
    """
    event is the tail of the notification_type, e.g. 'created', 'approved'.
    Never raises — a notification failure must not roll back the referral.
    """
    print("=" * 70, flush=True)
    print(f"[REF-NOTIFY] START referral={referral.pk} ref_id={referral.reference_id} "
          f"event={event} notify_admins={notify_admins} notify_doctors={notify_doctors}",
          flush=True)

    handler = NotificationSignalHandler()
    type_name = f'referral_{event}'

    title_map = {
        'created':      'New referral submitted',
        'under_review': 'Referral under review',
        'approved':     'Referral approved',
        'scheduled':    'Referral scheduled',
        'completed':    'Referral completed',
        'rejected':     'Referral rejected',
        'cancelled':    'Referral cancelled',
    }
    title = title_map.get(event, f'Referral {event}')
    print(f"[REF-NOTIFY] type_name={type_name!r} title={title!r}", flush=True)

    msg = (
        f'Referral {referral.reference_id} for {referral.full_name} '
        f'is now: {referral.get_status_display()}.'
    )
    print(f"[REF-NOTIFY] message={msg!r}", flush=True)

    def _safe(fn, **kw):
        user = kw.get('user')
        print(
            f"[REF-NOTIFY]   -> create_notification user={getattr(user, 'id', None)} "
            f"({getattr(user, 'get_username', lambda: '?')()}) "
            f"type={kw.get('notification_type')} priority={kw.get('priority')}",
            flush=True,
        )
        try:
            result = fn(**kw)
            print(f"[REF-NOTIFY]   ✓ OK -> notification_pk={getattr(result, 'pk', None)} "
                  f"notification_id={getattr(result, 'notification_id', None)}",
                  flush=True)
            return result
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception(
                'referral notification failed (type=%s, referral=%s)',
                kw.get('notification_type'), referral.pk,
            )
            print(
                f"[REF-NOTIFY]   ✗ FAILED user={getattr(user, 'id', None)} "
                f"type={kw.get('notification_type')}: {type(exc).__name__}: {exc}",
                flush=True,
            )
            return None

    # ── Admins ─────────────────────────────────────
    if notify_admins:
        admins = list(_referral_admin_recipients())
        print(f"[REF-NOTIFY] admins resolved: count={len(admins)}", flush=True)
        for a in admins:
            print(f"[REF-NOTIFY]   admin candidate: id={a.id} username={a.get_username()} "
                  f"is_staff={a.is_staff} is_superuser={a.is_superuser}",
                  flush=True)

        if not admins:
            print("[REF-NOTIFY]   ⚠ no admins found — check Profile.role / is_staff",
                  flush=True)

        for admin in admins:
            _safe(
                handler.create_notification,
                user=admin,
                notification_type=type_name,
                title=title,
                message=msg,
                priority='high',
                related_object_id=str(referral.pk),
                related_object_type='specialist_referral',
                related_url=f'/admin/referrals/{referral.pk}/',
                data={'reference_id': referral.reference_id},
            )
    else:
        print("[REF-NOTIFY] admins skipped (notify_admins=False)", flush=True)

    # ── Doctors ────────────────────────────────────
    if notify_doctors:
        doctors = list(_referral_doctor_recipients(referral))
        print(f"[REF-NOTIFY] doctors resolved: count={len(doctors)}", flush=True)
        for d in doctors:
            print(f"[REF-NOTIFY]   doctor candidate: id={d.id} username={d.get_username()}",
                  flush=True)

        if not doctors:
            print("[REF-NOTIFY]   ⚠ no doctors resolved — referral not assigned yet?",
                  flush=True)

        for doctor_user in doctors:
            _safe(
                handler.create_notification,
                user=doctor_user,
                notification_type=type_name,
                title=title,
                message=msg,
                priority='high',
                related_object_id=str(referral.pk),
                related_object_type='specialist_referral',
                related_url=f'/referrals/{referral.pk}/',
                data={'reference_id': referral.reference_id},
            )
    else:
        print("[REF-NOTIFY] doctors skipped (notify_doctors=False)", flush=True)

    print(f"[REF-NOTIFY] END referral={referral.pk} event={event}", flush=True)
    print("=" * 70, flush=True)
    
# def _create_referral_notifications(referral, event, *, notify_admins=True, notify_doctors=True):
#     """
#     event is the tail of the notification_type, e.g. 'created', 'approved'.
#     Never raises — a notification failure must not roll back the referral.
#     """
#     handler = NotificationSignalHandler()
#     type_name = f'referral_{event}'

#     title_map = {
#         'created':      'New referral submitted',
#         'under_review': 'Referral under review',
#         'approved':     'Referral approved',
#         'scheduled':    'Referral scheduled',
#         'completed':    'Referral completed',
#         'rejected':     'Referral rejected',
#         'cancelled':    'Referral cancelled',
#     }
#     title = title_map.get(event, f'Referral {event}')

#     msg = (
#         f'Referral {referral.reference_id} for {referral.full_name} '
#         f'is now: {referral.get_status_display()}.'
#     )

#     def _safe(fn, **kw):
#         try:
#             fn(**kw)
#         except Exception:
#             import logging
#             logging.getLogger(__name__).exception(
#                 'referral notification failed (type=%s, referral=%s)',
#                 kw.get('notification_type'), referral.pk,
#             )

#     if notify_admins:
#         for admin in _referral_admin_recipients():
#             _safe(
#                 handler.create_notification,
#                 user=admin,
#                 notification_type=type_name,
#                 title=title,
#                 message=msg,
#                 priority='high',          # bypasses quiet hours
#                 related_object_id=str(referral.pk),
#                 related_object_type='specialist_referral',
#                 related_url=f'/admin/referrals/{referral.pk}/',
#                 data={'reference_id': referral.reference_id},
#             )

#     if notify_doctors:
#         for doctor_user in _referral_doctor_recipients(referral):
#             _safe(
#                 handler.create_notification,
#                 user=doctor_user,
#                 notification_type=type_name,
#                 title=title,
#                 message=msg,
#                 priority='high',
#                 related_object_id=str(referral.pk),
#                 related_object_type='specialist_referral',
#                 related_url=f'/referrals/{referral.pk}/',
#                 data={'reference_id': referral.reference_id},
#             )    
            

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
    if created:
        _send_referral_email(instance, template='referral_received')
        _create_referral_notifications(
            instance, 'created',
            notify_admins=True,
            notify_doctors=False,     # see "who gets what" below
        )
        return

    previous = getattr(instance, '_previous_status', None)
    if previous == instance.status:
        return

    _send_referral_email(instance, template=f'referral_{instance.status}')
    _create_referral_notifications(
        instance, instance.status,
        notify_admins=True,
        notify_doctors=(instance.status in {'approved', 'scheduled', 'completed', 'cancelled'}),
    )