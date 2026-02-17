"""Shared OpenAI client — reads API key from user's stored keys."""

import base64

from openai import AsyncOpenAI
from sqlmodel import Session, select

from app.config import settings
from app.models.common import ApiKey


def _decrypt_key(encrypted: str) -> str:
    """Decrypt an API key. Mirrors settings.py logic."""
    try:
        from cryptography.fernet import Fernet

        key = settings.encryption_key
        if key and key != "change-me-in-production":
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.decrypt(encrypted.encode()).decode()
    except Exception:
        pass
    return base64.b64decode(encrypted.encode()).decode()


def get_openai_key(user_id: int, db: Session) -> str | None:
    """Get the decrypted OpenAI API key for a user."""
    api_key = db.exec(
        select(ApiKey).where(
            ApiKey.user_id == user_id,
            ApiKey.provider == "openai",
        )
    ).first()
    if not api_key:
        return None
    return _decrypt_key(api_key.encrypted_key)


def get_openai_client(user_id: int, db: Session) -> AsyncOpenAI:
    """Create an AsyncOpenAI client using the user's stored API key."""
    key = get_openai_key(user_id, db)
    if not key:
        raise ValueError("No OpenAI API key configured. Add one in Settings.")
    return AsyncOpenAI(api_key=key)
