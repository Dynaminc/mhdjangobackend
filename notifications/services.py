# notifications/services.py
import logging

from django.conf import settings
from firebase_admin import messaging

from .firebase import get_firebase_app
from .models import BrowserDevice

logger = logging.getLogger(__name__)


def send_push_to_user(user, title: str, body: str, url: str = "/dashboard"):
    app = get_firebase_app()

    # fcm_options.link must be ABSOLUTE HTTPS. localhost / http:// is rejected.
    frontend = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    absolute_link = f"{frontend}{url}" if frontend.startswith("https://") else None

    devices = BrowserDevice.objects.filter(user=user)
    results = []

    for device in devices.iterator():
        kwargs = {
            "notification": messaging.Notification(title=title, body=body),
            "data": {"url": url},
            "token": device.token,
        }

        # only attach webpush block when we have a valid HTTPS link
        if absolute_link:
            kwargs["webpush"] = messaging.WebpushConfig(
                fcm_options=messaging.WebpushFCMOptions(link=absolute_link),
            )

        message = messaging.Message(**kwargs)

        try:
            message_id = messaging.send(message, app=app)
            results.append({
                "device_id": device.pk,
                "success": True,
                "message_id": message_id,
            })

        except messaging.UnregisteredError:
            device.delete()
            results.append({
                "device_id": device.pk,
                "success": False,
                "error": "unregistered",
            })

        except Exception as e:
            logger.exception(
                "Firebase send failed for device %s (user %s)",
                device.pk, device.user_id,
            )
            results.append({
                "device_id": device.pk,
                "success": False,
                "error": "send_failed",
                "detail": f"{type(e).__name__}: {e}",
            })

    return results