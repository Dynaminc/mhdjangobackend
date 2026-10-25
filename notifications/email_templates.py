# notifications/email_templates.py
"""
All transactional email templates for Marvelle Healthcare, in one file.

Public API (what views call):
    send_verify_email(user, verify_url, expires_hours=24)
    send_reset_password_email(user, reset_url, expires_hours=1)
    send_referral_email(user, patient_name, reference_id, next_steps=None)

Each wrapper:
    • renders the Marvelle base layout with the right body
    • builds a matching plain-text fallback
    • sends a multipart/alternative EmailMultiAlternatives
"""

import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════
def _safe(value) -> str:
    """HTML-escape any user-supplied value before embedding it."""
    return escape(str(value or ""))


def _year() -> int:
    return datetime.now().year


def _button(url: str, label: str) -> str:
    """Green CTA button + copy-paste fallback link."""
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0;">
<tr>
<td style="border-radius:8px;background:#4dbb77;">
    <a href="{_safe(url)}" target="_blank"
       style="display:inline-block;padding:14px 28px;font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:8px;">
        {_safe(label)}
    </a>
</td>
</tr>
</table>

<p style="font-size:12px;color:#8f9495;line-height:1.6;margin:0 0 6px;">
    Or copy this link into your browser:
</p>
<p style="font-size:12px;color:#4dbb77;line-height:1.6;word-break:break-all;margin:0;">
    <a href="{_safe(url)}" style="color:#4dbb77;text-decoration:none;">{_safe(url)}</a>
</p>
"""


def _base(*, page_title, header_subtitle, header_title, content, footer_note):
    """Wrap the given body content in the shared Marvelle email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{_safe(page_title)}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f5f5;padding:32px 16px;">
<tr><td align="center">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

<!-- HEADER -->
<tr>
<td style="background:linear-gradient(135deg,#042b31 0%,#08606c 100%);padding:32px 32px 24px;text-align:center;">
    <span style="font-size:24px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
        Marvelle <span style="color:#6fe29b;">Healthcare</span>
    </span>
    <div style="color:rgba(255,255,255,0.7);font-size:11px;margin-top:10px;letter-spacing:2px;text-transform:uppercase;">
        {_safe(header_subtitle)}
    </div>
</td>
</tr>

<!-- BODY -->
<tr>
<td style="padding:36px 32px 24px;">
    <h1 style="font-size:22px;font-weight:700;color:#042b31;margin:0 0 12px;line-height:1.3;">
        {header_title}
    </h1>
    {content}
</td>
</tr>

<!-- FOOTER -->
<tr>
<td style="background:#fafbfb;padding:24px 32px;text-align:center;border-top:1px solid #eceded;">
    <div style="font-weight:700;color:#06444d;font-size:14px;margin-bottom:6px;">Marvelle Healthcare</div>
    <div style="font-size:12px;color:#8f9495;line-height:1.6;">
        {footer_note}
    </div>
    <div style="font-size:11px;color:#abafaf;margin-top:14px;">
        © {_year()} Marvelle Health. All rights reserved.
    </div>
</td>
</tr>

</table>

</td></tr>
</table>

</body>
</html>
"""


def _send(*, to, subject, html, text, from_email=None, fail_silently=False):
    """Send a multipart/alternative email (HTML + plain-text fallback)."""
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=list(to),
    )
    msg.attach_alternative(html, "text/html")
    try:
        sent = msg.send(fail_silently=fail_silently)
        return sent > 0
    except Exception:
        logger.exception("Email send failed: subject=%s to=%s", subject, to)
        if not fail_silently:
            raise
        return False


def _display_name(user) -> str:
    return user.get_full_name() or user.first_name or user.email


# ═════════════════════════════════════════════════════════════════
# 1. Verify email
# ═════════════════════════════════════════════════════════════════
def _verify_html(user, verify_url, expires_hours):
    content = f"""
    <p style="color:#5a6162;font-size:15px;line-height:1.65;margin:0 0 18px;">
        Thank you for signing up to <strong style="color:#06444d;">Marvelle Healthcare</strong>.
        Please confirm your email address to activate your MHPro account.
    </p>

    {_button(verify_url, 'Verify my email')}

    <p style="color:#5a6162;font-size:15px;line-height:1.65;margin:24px 0 0;">
        This link expires in <strong>{expires_hours} hours</strong>.
        If you didn't create this account, you can safely ignore this email.
    </p>

    <p style="color:#8f9495;font-size:13px;line-height:1.6;margin:24px 0 0;padding:16px;background:#fafbfb;border-radius:10px;">
        🔒 <strong style="color:#5a6162;">Your data is protected.</strong>
        Your personal information is stored securely and used solely for the purpose
        of providing healthcare services.
    </p>
    """
    return _base(
        page_title="Verify your MHPro account",
        header_subtitle="Account Verification",
        header_title=f"Welcome, {_safe(_display_name(user))} 👋",
        content=content,
        footer_note=(
            "This is an automated message from Marvelle Healthcare.<br/>"
            "If you did not sign up, please ignore this email."
        ),
    )


def _verify_text(user, verify_url, expires_hours):
    return (
        f"Welcome, {_display_name(user)}!\n\n"
        "Thank you for signing up to Marvelle Healthcare. Please confirm your "
        "email address to activate your MHPro account by opening the link below:\n\n"
        f"{verify_url}\n\n"
        f"This link expires in {expires_hours} hours.\n\n"
        "If you didn't create this account, you can safely ignore this email.\n\n"
        f"---\nMarvelle Healthcare · © {_year()} Marvelle Health. All rights reserved.\n"
    )


def send_verify_email(user, verify_url, expires_hours=24, **kwargs):
    return _send(
        to=[user.email],
        subject="Verify your MHPro account",
        html=_verify_html(user, verify_url, expires_hours),
        text=_verify_text(user, verify_url, expires_hours),
        **kwargs,
    )


# ═════════════════════════════════════════════════════════════════
# 2. Reset password
# ═════════════════════════════════════════════════════════════════
def _reset_html(user, reset_url, expires_hours):
    content = f"""
    <p style="color:#5a6162;font-size:15px;line-height:1.65;margin:0 0 18px;">
        Hi {_safe(_display_name(user))}, we received a request to reset the password
        on your <strong style="color:#06444d;">Marvelle Healthcare</strong> account.
    </p>

    {_button(reset_url, 'Reset my password')}

    <p style="color:#5a6162;font-size:15px;line-height:1.65;margin:24px 0 0;">
        This link expires in <strong>{expires_hours} hour{'s' if expires_hours != 1 else ''}</strong>.
        If you didn't request a password reset, you can safely ignore this email —
        your password will not change.
    </p>

    <p style="color:#8f9495;font-size:13px;line-height:1.6;margin:24px 0 0;padding:16px;background:#fafbfb;border-radius:10px;">
        🔒 <strong style="color:#5a6162;">Security tip.</strong>
        Marvelle Healthcare will never ask you to share this link or your new
        password over email, phone, or chat.
    </p>
    """
    return _base(
        page_title="Reset your MHPro password",
        header_subtitle="Password Reset",
        header_title="Reset your password 🔐",
        content=content,
        footer_note=(
            "This is an automated message from Marvelle Healthcare.<br/>"
            "If you did not request a password reset, please ignore this email."
        ),
    )


def _reset_text(user, reset_url, expires_hours):
    plural = "s" if expires_hours != 1 else ""
    return (
        f"Hi {_display_name(user)},\n\n"
        "We received a request to reset the password on your Marvelle Healthcare account.\n\n"
        "Open the link below to set a new password:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {expires_hours} hour{plural}.\n\n"
        "If you didn't request a password reset, you can safely ignore this email — "
        "your password will not change.\n\n"
        f"---\nMarvelle Healthcare · © {_year()} Marvelle Health. All rights reserved.\n"
    )


def send_reset_password_email(user, reset_url, expires_hours=1, **kwargs):
    return _send(
        to=[user.email],
        subject="Reset your MHPro password",
        html=_reset_html(user, reset_url, expires_hours),
        text=_reset_text(user, reset_url, expires_hours),
        **kwargs,
    )


# ═════════════════════════════════════════════════════════════════
# 3. Referral received
# ═════════════════════════════════════════════════════════════════
_DEFAULT_STEPS = [
    {"title": "Review",       "body": "Our MHPro doctors assess your complaint."},
    {"title": "Approval",     "body": "You'll receive an email once approved."},
    {"title": "Scheduling",   "body": "Pick a time that works for you."},
    {"title": "Consultation", "body": "Meet your Marvelle Health doctor."},
]


def _steps_html(steps):
    rows = ""
    for i, step in enumerate(steps, start=1):
        rows += f"""
        <tr>
        <td style="width:32px;vertical-align:top;padding-bottom:12px;">
            <div style="width:24px;height:24px;border-radius:50%;background:#dcf8e7;color:#22653b;text-align:center;line-height:24px;font-size:12px;font-weight:700;">
                {i}
            </div>
        </td>
        <td style="font-size:14px;color:#40494a;line-height:1.5;padding-bottom:12px;">
            <strong style="color:#05373e;">{_safe(step['title'])}</strong> — {_safe(step['body'])}
        </td>
        </tr>
        """
    return rows


def _referral_html(patient_name, reference_id, steps):
    content = f"""
    <p style="color:#5a6162;font-size:15px;line-height:1.65;margin:0 0 18px;">
        Thank you for reaching out to <strong style="color:#06444d;">Marvelle Healthcare</strong>.
        We have successfully received your specialist referral request.
    </p>

    <p style="color:#5a6162;font-size:15px;line-height:1.65;margin:0 0 24px;">
        Your request has been logged and will be assessed by our Marvelle Healthcare
        doctor team. We'll review your complaint carefully and, if a specialist referral
        is appropriate, we'll be in touch with next steps.
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:#f1fcf5;border-left:4px solid #4dbb77;border-radius:8px;margin:24px 0;">
    <tr><td style="padding:16px 20px;">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#4fa06e;font-weight:700;margin-bottom:4px;">
            Your Reference ID
        </div>
        <div style="font-family:'Courier New',monospace;font-size:16px;font-weight:700;color:#05373e;letter-spacing:1px;">
            {_safe(reference_id)}
        </div>
    </td></tr>
    </table>

    <div style="background:#fafbfb;border-radius:12px;padding:20px;margin:24px 0;">
        <div style="font-size:14px;font-weight:700;color:#06444d;margin-bottom:12px;">
            What happens next
        </div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            {_steps_html(steps)}
        </table>
    </div>

    <p style="color:#8f9495;font-size:13px;line-height:1.6;margin:24px 0 0;padding:16px;background:#fafbfb;border-radius:10px;">
        🔒 <strong style="color:#5a6162;">Your data is protected.</strong>
        Your personal and health information is stored securely and processed solely
        for the purpose of setting up consultations with the Marvelle Health doctor team.
    </p>
    """
    return _base(
        page_title="Welcome to MHPro",
        header_subtitle="Specialist Referral System",
        header_title=f"Welcome, {_safe(patient_name)} 👋",
        content=content,
        footer_note=(
            "This is an automated message from the Marvelle Healthcare "
            "Specialist Referral System.<br/>"
            "If you did not submit this request, please ignore this email."
        ),
    )


def _referral_text(patient_name, reference_id, steps):
    lines = [
        f"Welcome, {patient_name}!",
        "",
        "Thank you for reaching out to Marvelle Healthcare. We have successfully "
        "received your specialist referral request.",
        "",
        f"Your Reference ID: {reference_id}",
        "",
        "What happens next:",
    ]
    for i, step in enumerate(steps, start=1):
        lines.append(f"  {i}. {step['title']} — {step['body']}")
    lines += [
        "",
        "Your personal and health information is stored securely and processed "
        "solely for the purpose of setting up consultations with the Marvelle "
        "Health doctor team.",
        "",
        f"---\nMarvelle Healthcare · © {_year()} Marvelle Health. All rights reserved.",
        "",
    ]
    return "\n".join(lines)


def send_referral_email(
    user, patient_name, reference_id, next_steps=None, **kwargs
):
    steps = next_steps or _DEFAULT_STEPS
    return _send(
        to=[user.email],
        subject="We received your Marvelle Healthcare referral",
        html=_referral_html(patient_name, reference_id, steps),
        text=_referral_text(patient_name, reference_id, steps),
        **kwargs,
    )