#!/usr/bin/env python3
"""One-time migration: encrypt existing plaintext API keys in app_settings.

Usage:
    cd backend
    python -m scripts.migrate_encrypt_keys

The script reads api_key / api_secret via SQLAlchemy (the EncryptedString
TypeDecorator auto-decrypts or falls back to plaintext), then forces a
re-write so that process_bind_param encrypts the value with Fernet.

Safe to run multiple times — already-encrypted values decrypt normally
and are re-encrypted identically (Fernet uses random IV, so the
ciphertext will differ, but that is harmless).

Requires FIELD_ENCRYPTION_KEY to be set in the environment / .env file.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package is importable when running from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm.attributes import flag_modified

from app.db import SessionLocal
from app.models import AppSettings


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.query(AppSettings).all()
        if not rows:
            print("No app_settings rows found. Nothing to migrate.")
            return

        migrated = 0
        for settings in rows:
            touched = False

            if settings.api_key:
                # Reading triggers process_result_value (decrypt / fallback).
                # Flag as modified so the UPDATE triggers process_bind_param.
                flag_modified(settings, "api_key")
                touched = True

            if settings.api_secret:
                flag_modified(settings, "api_secret")
                touched = True

            if touched:
                migrated += 1

        if migrated:
            db.commit()
            print(f"✅ Migrated {migrated} row(s): API keys are now encrypted at rest.")
        else:
            print("No plaintext API keys found. Nothing to migrate.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
