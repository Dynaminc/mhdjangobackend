# apps/accounts/tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator

# class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
#     def _make_hash_value(self, user, timestamp):
#         return f"{user.pk}{user.email}{user.profile.email_verified}{timestamp}"

# email_verification_token = EmailVerificationTokenGenerator()

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Hash only stable user fields.
    Do NOT hash Profile fields (they change during verification).
    Do NOT hash last_login (auto-login on register changes it).
    """
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.password}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()