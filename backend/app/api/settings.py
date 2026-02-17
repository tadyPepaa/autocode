"""Settings API endpoints — API key management."""

import base64
from datetime import datetime

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models.common import ApiKey
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])

# Supported providers
PROVIDERS = {"openai", "anthropic", "google", "mistral", "other"}


# --- Encryption helpers ---


def _get_fernet() -> Fernet | None:
    """Return Fernet instance if encryption_key is configured, else None."""
    key = settings.encryption_key
    if not key or key == "change-me-in-production":
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None


def encrypt_key(raw_key: str) -> str:
    """Encrypt an API key. Uses Fernet if available, else base64."""
    f = _get_fernet()
    if f:
        return f.encrypt(raw_key.encode()).decode()
    return base64.b64encode(raw_key.encode()).decode()


def decrypt_key(encrypted: str) -> str:
    """Decrypt an API key. Uses Fernet if available, else base64."""
    f = _get_fernet()
    if f:
        try:
            return f.decrypt(encrypted.encode()).decode()
        except Exception:
            pass
    return base64.b64decode(encrypted.encode()).decode()


def mask_key(raw_key: str) -> str:
    """Mask an API key, showing only last 4 chars."""
    if len(raw_key) <= 4:
        return "****"
    return "*" * (len(raw_key) - 4) + raw_key[-4:]


# --- Pydantic models ---


class ApiKeyCreate(BaseModel):
    provider: str
    key: str


class ApiKeyResponse(BaseModel):
    id: int
    provider: str
    masked_key: str
    created_at: datetime


# --- Endpoints ---


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all API keys for the current user with masked values."""
    keys = db.exec(
        select(ApiKey).where(ApiKey.user_id == user.id)
    ).all()
    result = []
    for k in keys:
        raw = decrypt_key(k.encrypted_key)
        result.append(
            ApiKeyResponse(
                id=k.id,
                provider=k.provider,
                masked_key=mask_key(raw),
                created_at=k.created_at,
            )
        )
    return result


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=201)
async def add_or_update_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add or update an API key for a provider."""
    if body.provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider. Must be one of: {', '.join(sorted(PROVIDERS))}",
        )
    if not body.key or not body.key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    # Check if key already exists for this provider
    existing = db.exec(
        select(ApiKey).where(
            ApiKey.user_id == user.id,
            ApiKey.provider == body.provider,
        )
    ).first()

    encrypted = encrypt_key(body.key.strip())

    if existing:
        existing.encrypted_key = encrypted
        existing.created_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        api_key = existing
    else:
        api_key = ApiKey(
            user_id=user.id,
            provider=body.provider,
            encrypted_key=encrypted,
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

    raw = decrypt_key(api_key.encrypted_key)
    return ApiKeyResponse(
        id=api_key.id,
        provider=api_key.provider,
        masked_key=mask_key(raw),
        created_at=api_key.created_at,
    )


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete an API key."""
    api_key = db.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(api_key)
    db.commit()
    return {"detail": "API key deleted"}
