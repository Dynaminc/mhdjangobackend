# apps/files/storage.py
import os, uuid
from django.conf import settings

from .crypto import encrypt, decrypt


# ═════════════════════════════════════════════════════════════
# LOCAL STORAGE (active)
# ═════════════════════════════════════════════════════════════
def save_file(raw: bytes) -> tuple[str, int]:
    """Encrypt raw bytes and write to MEDIA_ROOT/secure_files/.
    Returns (relative_path, encrypted_size)."""
    encrypted = encrypt(raw)
    rel = f"secure_files/{uuid.uuid4().hex}.bin"
    full = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'wb') as fh:
        fh.write(encrypted)
    return rel, len(encrypted)


def read_file(rel_path: str) -> bytes:
    """Read encrypted bytes from disk and decrypt."""
    full = os.path.join(settings.MEDIA_ROOT, rel_path)
    with open(full, 'rb') as fh:
        return decrypt(fh.read())


def delete_file(rel_path: str) -> None:
    full = os.path.join(settings.MEDIA_ROOT, rel_path)
    if os.path.exists(full):
        os.remove(full)


# ═════════════════════════════════════════════════════════════
# S3 STORAGE (commented out — swap in when ready)
# ═════════════════════════════════════════════════════════════
# import boto3
#
# s3 = boto3.client(
#     's3',
#     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#     region_name=settings.AWS_S3_REGION_NAME,
# )
#
# def save_file(raw: bytes) -> tuple[str, int]:
#     encrypted = encrypt(raw)
#     key = f"secure_files/{uuid.uuid4().hex}.bin"
#     s3.put_object(
#         Bucket=settings.AWS_STORAGE_BUCKET_NAME,
#         Key=key,
#         Body=encrypted,
#     )
#     return key, len(encrypted)
#
# def read_file(key: str) -> bytes:
#     obj = s3.get_object(
#         Bucket=settings.AWS_STORAGE_BUCKET_NAME,
#         Key=key,
#     )
#     return decrypt(obj['Body'].read())
#
# def delete_file(key: str) -> None:
#     s3.delete_object(
#         Bucket=settings.AWS_STORAGE_BUCKET_NAME,
#         Key=key,
#     )