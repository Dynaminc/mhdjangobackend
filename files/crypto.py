# apps/files/crypto.py
import base64, hashlib
from cryptography.fernet import Fernet
from django.conf import settings

_key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
_fernet = Fernet(_key)


def encrypt(raw: bytes) -> bytes:
    return _fernet.encrypt(raw)


def decrypt(token: bytes) -> bytes:
    return _fernet.decrypt(token)