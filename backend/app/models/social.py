from datetime import datetime

from sqlmodel import Field, SQLModel


class SocialAccount(SQLModel, table=True):
    __tablename__ = "social_accounts"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    platform: str
    access_token: str = Field(default="")  # encrypted
    account_name: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
