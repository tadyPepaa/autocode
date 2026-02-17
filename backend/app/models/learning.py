from datetime import datetime

from sqlmodel import Field, SQLModel


class LearningSubject(SQLModel, table=True):
    __tablename__ = "learning_subjects"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningCourse(SQLModel, table=True):
    __tablename__ = "learning_courses"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    subject_id: int = Field(foreign_key="learning_subjects.id", index=True)
    name: str
    instructions: str = Field(default="")
    chat_history_path: str = Field(default="")
    student_notes_path: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
