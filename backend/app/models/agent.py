from datetime import datetime

from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    __tablename__ = "agents"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str
    type: str  # "coding" | "research" | "learning" | "social_media" | "custom"
    model: str
    identity: str = Field(default="")
    tools: str = Field(default="[]")  # JSON
    mcp_servers: str = Field(default="[]")  # JSON
    global_rules: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
