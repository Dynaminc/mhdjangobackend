# notifications/firebase.py
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials

_BASE_DIR = Path(__file__).resolve().parent


def get_firebase_app():
    """Initialise (once) and return the firebase-admin app."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    if not raw:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_PATH is not set. "
            "Point it at mhprohermes.json (relative or absolute)."
        )

    # Strip any leading slash so a Windows env like "/mhprohermes.json"
    # doesn't get interpreted as "root of the C: drive".
    p = Path(raw.lstrip("/\\"))
    credential_path = p if p.is_absolute() else _BASE_DIR / p

    if not credential_path.is_file():
        raise FileNotFoundError(
            f"Firebase service-account JSON not found.\n"
            f"  env var       : {raw!r}\n"
            f"  resolved path : {credential_path}\n"
            f"  module dir    : {_BASE_DIR}"
        )

    cred = credentials.Certificate(str(credential_path))
    return firebase_admin.initialize_app(cred)