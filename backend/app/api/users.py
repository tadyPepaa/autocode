import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_admin_user
from app.auth import hash_password
from app.config import settings
from app.database import get_session
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime


@router.get("", response_model=list[UserResponse])
async def list_users(
    session: Session = Depends(get_session),
    _admin: User = Depends(get_admin_user),
):
    users = session.exec(select(User)).all()
    return users


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_admin_user),
):
    existing = session.exec(
        select(User).where(User.username == body.username)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        **({"role": body.role} if body.role else {}),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Create workspace directories
    user_dir = Path(settings.data_dir) / body.username
    for subdir in ("projects", "research", "learning", "config"):
        (user_dir / subdir).mkdir(parents=True, exist_ok=True)

    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_admin_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove workspace directory
    user_dir = Path(settings.data_dir) / user.username
    if user_dir.exists():
        shutil.rmtree(user_dir)

    session.delete(user)
    session.commit()
    return {"detail": "User deleted"}
