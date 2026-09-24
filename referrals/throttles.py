# apps/specialists/throttles.py
from rest_framework.throttling import SimpleRateThrottle
from django.core.cache import cache


class ReferralAnonThrottle(SimpleRateThrottle):
    """
    Limit anonymous referral submissions by IP address.
    e.g. 5 submissions per hour per IP
    """
    scope = 'referral_anon'

    def get_cache_key(self, request, view):
        # Only throttle unauthenticated users
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class ReferralEmailThrottle(SimpleRateThrottle):
    """
    Limit referral submissions by the submitted email.
    e.g. 3 submissions per day per email
    """
    scope = 'referral_email'

    def get_cache_key(self, request, view):
        email = None
        if isinstance(request.data, dict):
            email = request.data.get('email')
        if not email:
            return None  # no email → let the anon throttle handle it
        return self.cache_format % {
            'scope': self.scope,
            'ident': email.lower().strip(),
        }


class ReferralUserThrottle(SimpleRateThrottle):
    """
    For authenticated patients — softer limit.
    e.g. 10 submissions per day per user
    """
    scope = 'referral_user'

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk,
        }