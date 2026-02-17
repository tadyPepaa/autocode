from datetime import datetime

from sqlmodel import Field, SQLModel


class ResearchSession(SQLModel, table=True):
    __tablename__ = "research_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    name: str
    slug: str
    status: str = Field(default="active")
    tmux_session: str = Field(default="")
    workspace_path: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
