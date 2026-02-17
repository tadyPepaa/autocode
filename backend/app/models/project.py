from datetime import datetime

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    name: str
    slug: str
    description: str = Field(default="")
    architecture: str = Field(default="")
    implementation_plan: str = Field(default="[]")  # JSON
    status: str = Field(default="pending")
    current_step: int = Field(default=0)
    tmux_session: str = Field(default="")
    workspace_path: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
