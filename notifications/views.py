import logging

from django.db import IntegrityError, transaction

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import BrowserDevice
from .serializers import RegisterDeviceSerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device(request):
    """
    Register (or refresh) the calling user's browser device token.

    Body:
        token (required) — FCM / Web Push registration token
    """
    # ── 1. Validate payload ─────────────────────────
    serializer = RegisterDeviceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    token = serializer.validated_data['token']
    user  = request.user

    # ── 2. Upsert device row atomically ─────────────
    with transaction.atomic():
        device = (
            BrowserDevice.objects
            .select_for_update()
            .filter(token=token)
            .first()
        )

        if device is None:
            try:
                device = BrowserDevice.objects.create(user=user, token=token)
                action_taken = 'created'
            except IntegrityError:
                # race: another request created it between SELECT and INSERT
                device = BrowserDevice.objects.get(token=token)
                action_taken = 'unchanged'
        elif device.user_id == user.pk:
            # same user re-registering — idempotent, no write
            action_taken = 'unchanged'
        else:
            # token now belongs to a different authenticated user
            previous_user_id = device.user_id
            device.user = user
            device.save(update_fields=['user', 'updated_at'])
            action_taken = 'reassigned'
            logger.warning(
                'BrowserDevice %s reassigned from user=%s to user=%s',
                device.pk, previous_user_id, user.pk,
            )

    # ── 3. Respond ──────────────────────────────────
    return Response(
        {
            'status': 'success',
            'message': 'Browser device registered.',
            'action': action_taken,
            'device_id': device.pk,
        },
        status=status.HTTP_200_OK,
    )
    
    
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from urllib.parse import quote

from .models import BrowserDevice
from .services import send_push_to_user


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def test_push(request):
    """
    Dev push tester with an HTML form.

      /api/v1/devices/test-push/                → send to YOUR devices
      /api/v1/devices/test-push/?user_id=31     → send to user 31's devices
      /api/v1/devices/test-push/?all=1          → send to EVERY device (dev only)

    Form fields post back as query params:
      title, body, url, user_id or all
    """
    qp = request.query_params
    title = qp.get("title", "")
    body = qp.get("body", "")
    url = qp.get("url", "/dashboard")
    target_all = qp.get("all") == "1"
    target_user_id = qp.get("user_id")

    # Only send when the user explicitly submitted the form
    do_send = qp.get("send") == "1"

    results = []
    if do_send:
        if target_all:
            for d in BrowserDevice.objects.select_related("user"):
                results.extend(send_push_to_user(d.user, title, body, url))
        elif target_user_id:
            from django.contrib.auth import get_user_model
            target = get_user_model().objects.filter(pk=target_user_id).first()
            if not target:
                return Response(
                    {"status": "error", "message": f"User {target_user_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            results = send_push_to_user(target, title, body, url)
        else:
            results = send_push_to_user(request.user, title, body, url)

    sent = [r for r in results if r["success"]]

    diag = {
        "current_user_id": request.user.id,
        "current_user_username": request.user.get_username(),
        "total_devices_in_system": BrowserDevice.objects.count(),
        "your_devices_count": BrowserDevice.objects.filter(user=request.user).count(),
        "all_devices": list(
            BrowserDevice.objects.values("id", "user_id", "updated_at")
        ),
    }

    # ── JSON response for API clients ────────────────
    if "text/html" not in request.headers.get("Accept", ""):
        return Response(
            {
                "status": "success" if sent else ("error" if do_send else "idle"),
                "message": (
                    f"Sent {len(sent)}/{len(results)} pushes."
                    if do_send else
                    "Form ready — pass ?send=1 with title/body to actually send."
                ),
                "sent": len(sent),
                "failed": len(results) - len(sent),
                "results": results,
                "diagnostics": diag,
            },
            status=status.HTTP_200_OK,
        )

    # ── HTML response — form + results + diagnostics ─
    result_rows = "".join(
        f"<li>device {r['device_id']}: "
        f"{'✅ <code>' + r['message_id'] + '</code>' if r['success'] else '❌ ' + r['error']}"
        f"{' — ' + r.get('detail','') if r.get('detail') else ''}</li>"
        for r in results
    ) or "<li><em>Nothing sent yet.</em></li>"

    device_rows = "".join(
        f"<li>device {d['id']} → user_id={d['user_id']} "
        f"(updated {d['updated_at']:%Y-%m-%d %H:%M})</li>"
        for d in diag["all_devices"]
    ) or "<li><em>None registered in the whole DB.</em></li>"

    # Prefill the form with whatever was in the query string
    banner = ""
    if do_send:
        color = "#155724" if sent else "#721c24"
        bg    = "#d4edda" if sent else "#f8d7da"
        banner = (
            f'<div style="background:{bg};color:{color};padding:.75rem 1rem;'
            f'border-radius:6px;margin-bottom:1rem;font-weight:600">'
            f'{"✅" if sent else "❌"} Sent {len(sent)}/{len(results)} push(es).'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Push tester</title>
<style>
  body {{ font: 15px system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }}
  label {{ display: block; margin: 1rem 0 .25rem; font-weight: 600; }}
  input, textarea {{ width: 100%; box-sizing: border-box; padding: .55rem; font: inherit; }}
  textarea {{ min-height: 70px; }}
  button {{ margin-top: 1rem; font: inherit; padding: .75rem 1.25rem;
            background: #0b5; color: #fff; border: 0; border-radius: 6px; cursor: pointer; }}
  fieldset {{ border: 1px solid #ddd; border-radius: 6px; padding: 1rem; margin-top: 1rem; }}
  .row {{ display: flex; gap: 1rem; }}
  .row > * {{ flex: 1; }}
  code {{ font-size: 13px; }}
  ul {{ padding-left: 1.25rem; }}
</style></head><body>

<h1>🔔 Push tester</h1>
<p>Logged in as <b>{diag['current_user_username']}</b> (id={diag['current_user_id']}).
Your devices: <b>{diag['your_devices_count']}</b> · Total in DB: <b>{diag['total_devices_in_system']}</b>.</p>

{banner}

<form method="get">
  <label for="title">Title</label>
  <input id="title" name="title" value="{title or 'Test push 🚀'}" required>

  <label for="body">Body (message)</label>
  <textarea id="body" name="body" required>{body or 'Hello from the push tester — this is a message you actually typed.'}</textarea>

  <label for="url">URL to open on click</label>
  <input id="url" name="url" value="{url}" placeholder="/dashboard">

  <fieldset>
    <legend>Target</legend>
    <label><input type="radio" name="_target" value="me" checked> My devices only</label>
    <label><input type="radio" name="_target" value="user"> Specific user id:</label>
    <input name="user_id" placeholder="e.g. 8" value="{target_user_id or ''}">
    <label><input type="radio" name="_target" value="all" {'checked' if target_all else ''}> All devices (dev only)</label>
  </fieldset>

  <input type="hidden" name="send" value="1">
  <button type="submit">Send push</button>
</form>

<h2>Results</h2>
<ul>{result_rows}</ul>

<h2>All devices</h2>
<ul>{device_rows}</ul>

<h2>Quick retry</h2>
<ul>
  <li><a href="?">open form</a></li>
  <li><a href="?all=1&send=1&title=Hello&body=Broadcast">broadcast a test</a></li>
</ul>

<script>
  // Radio buttons drive user_id / all hidden handling
  document.querySelector('form').addEventListener('submit', (e) => {{
    const t = document.querySelector('input[name="_target"]:checked')?.value;
    const form = e.target;
    form.querySelector('input[name="user_id"]').disabled = (t !== 'user');
    if (t === 'all') {{
      const h = document.createElement('input');
      h.type = 'hidden'; h.name = 'all'; h.value = '1';
      form.appendChild(h);
    }}
  }});
</script>

</body></html>"""
    return HttpResponse(html)
