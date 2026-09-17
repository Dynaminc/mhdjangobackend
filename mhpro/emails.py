# your_app/emails.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _send(subject, to_email, template_name, context):
    html = render_to_string(f'emails/{template_name}.html', context)
    text = strip_tags(html)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)


def send_signup_mail(user):
    _send(
        subject='Welcome to MHPro',
        to_email=user.email,
        template_name='signup',
        context={
            'first_name': user.first_name or user.username,
            'login_url': f'{settings.FRONTEND_URL}/login',
        },
    )


def send_password_reset_mail(user, reset_url):
    """
    Sends a reset mail. The template differs based on how the account was created.
    - Google signup (no usable password): user must reset via Google, not a password form.
    - Normal signup: normal reset link.
    """
    is_google_account = not user.has_usable_password()

    if is_google_account:
        _send(
            subject='About your MHPro account',
            to_email=user.email,
            template_name='reset_google',
            context={
                'first_name': user.first_name or user.username,
                'login_url': f'{settings.FRONTEND_URL}/login',
            },
        )
    else:
        _send(
            subject='Reset your MHPro password',
            to_email=user.email,
            template_name='reset_password',
            context={
                'first_name': user.first_name or user.username,
                'reset_url': reset_url,
                'expiry_hours': 24,
            },
        )