# notifications/services.py
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError

from .firebase import get_firebase_app
from .models import BrowserDevice

logger = logging.getLogger(__name__)

MAX_TITLE_LEN = 200
MAX_BODY_LEN  = 1000   # stay well under FCM's 4 KB envelope cap


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def send_push_to_user(
    user,
    title: str,
    body: str,
    url: str = "/dashboard",
    data: dict | None = None,
):
    """
    Send a push to every BrowserDevice belonging to `user`.
    Returns a list of per-device result dicts.
    """
    app = get_firebase_app()

    title = _truncate(title, MAX_TITLE_LEN)
    body  = _truncate(body,  MAX_BODY_LEN)

    frontend = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    absolute_link = f"{frontend}{url}" if frontend.startswith("https://") else None

    devices = list(BrowserDevice.objects.filter(user=user))
    if not devices:
        logger.info("no browser devices for user %s", user.pk)
        return []

    # FCM data values MUST be strings.
    base_data = {"url": url}
    if data:
        base_data.update({k: str(v) for k, v in data.items() if v is not None})

    results = []

    for device in devices:
        try:
            kwargs = {
                "notification": messaging.Notification(title=title, body=body),
                "data": base_data,
                "token": device.token,
            }
            if absolute_link:
                kwargs["webpush"] = messaging.WebpushConfig(
                    fcm_options=messaging.WebpushFCMOptions(link=absolute_link),
                )
            message = messaging.Message(**kwargs)
            message_id = messaging.send(message, app=app)

            results.append({
                "device_id": device.pk,
                "token_prefix": device.token[:20],
                "success": True,
                "message_id": message_id,
            })

        except messaging.UnregisteredError:
            # expired / uninstalled — remove so we stop wasting sends
            device.delete()
            results.append({
                "device_id": device.pk,
                "token_prefix": device.token[:20],
                "success": False,
                "error": "unregistered",
            })

        except messaging.SenderIdMismatchError:
            # token is from a different Firebase project — dead to us
            device.delete()
            results.append({
                "device_id": device.pk,
                "token_prefix": device.token[:20],
                "success": False,
                "error": "sender_mismatch",
            })

        except FirebaseError as e:
            logger.exception(
                "FCM error for device %s (user %s)", device.pk, device.user_id,
            )
            results.append({
                "device_id": device.pk,
                "token_prefix": device.token[:20],
                "success": False,
                "error": "fcm_error",
                "detail": f"{type(e).__name__}: {e}",
            })

        except Exception as e:
            logger.exception(
                "Unexpected push failure for device %s (user %s)",
                device.pk, device.user_id,
            )
            results.append({
                "device_id": device.pk,
                "token_prefix": device.token[:20],
                "success": False,
                "error": "send_failed",
                "detail": f"{type(e).__name__}: {e}",
            })

    return results


def dispatch_notification(notification):
    """
    Turn a Notification row into a real browser push.
    Idempotent, respects push_enabled, updates delivered_* fields.
    """
    try:
        prefs = notification.user.notification_preferences
    except ObjectDoesNotExist:
        prefs = None

    if prefs is not None and not prefs.push_enabled:
        logger.info(
            "push skipped for notification %s — push disabled for user %s",
            notification.pk, notification.user_id,
        )
        return []

    if notification.is_delivered:
        return []

    results = send_push_to_user(
        user=notification.user,
        title=notification.title,
        body=notification.body or notification.message or "",
        url=notification.related_url or "/dashboard",
        data={
            "notification_id":   notification.notification_id,
            "notification_type": notification.notification_type,
            "priority":          notification.priority,
            "related_object_id": notification.related_object_id,
            "related_object_type": notification.related_object_type,
        },
    )

    sent   = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    if sent:
        notification.is_delivered  = True
        notification.delivered_at  = timezone.now()
        notification.delivered_via = "push"
        notification.save(update_fields=[
            "is_delivered", "delivered_at", "delivered_via",
        ])

    if failed:
        logger.warning(
            "push delivery failed for notification %s (%d/%d devices): %s",
            notification.pk, len(failed), len(results),
            "; ".join(r.get("error", "?") for r in failed),
        )

    return results