from datetime import datetime

from sqlmodel import Field, SQLModel


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_type: str  # "project" | "research" | "learning"
    session_id: int
    role: str  # "user" | "assistant"
    content: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentInstance(SQLModel, table=True):
    __tablename__ = "agent_instances"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    project_id: int | None = Field(default=None, foreign_key="projects.id")
    pid: int | None = Field(default=None)
    status: str = Field(default="stopped")  # "running" | "stopped" | "error"
    started_at: datetime | None = Field(default=None)
    stopped_at: datetime | None = Field(default=None)


class Log(SQLModel, table=True):
    __tablename__ = "logs"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key="projects.id")
    agent_instance_id: int | None = Field(
        default=None, foreign_key="agent_instances.id"
    )
    level: str = Field(default="info")  # "debug" | "info" | "warning" | "error"
    message: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    provider: str  # "openai" | "anthropic" | etc.
    encrypted_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
