import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models.agent import Agent
from app.models.common import ChatMessage
from app.models.learning import LearningCourse, LearningSubject
from app.models.user import User
from app.services.learning_agent import learning_agent

router = APIRouter(tags=["learning"])


def _generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# --- Pydantic models ---


class CreateSubjectRequest(BaseModel):
    name: str


class CreateCourseRequest(BaseModel):
    name: str
    instructions: str = ""


class SendMessageRequest(BaseModel):
    content: str


class SubjectResponse(BaseModel):
    id: int
    user_id: int
    agent_id: int
    name: str
    slug: str
    workspace_path: str
    created_at: datetime


class CourseResponse(BaseModel):
    id: int
    user_id: int
    subject_id: int
    name: str
    slug: str
    instructions: str
    chat_history_path: str
    student_notes_path: str
    workspace_path: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: int
    user_id: int
    session_type: str
    session_id: int
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    message: str


# --- Helpers ---


def _get_agent_or_404(agent_id: int, user: User, db: Session) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _get_subject_or_404(
    subject_id: int, user: User, db: Session
) -> LearningSubject:
    subject = db.get(LearningSubject, subject_id)
    if not subject or subject.user_id != user.id:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


def _get_course_or_404(
    course_id: int, user: User, db: Session
) -> LearningCourse:
    course = db.get(LearningCourse, course_id)
    if not course or course.user_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# --- Subject Endpoints ---


@router.post(
    "/agents/{agent_id}/subjects",
    response_model=SubjectResponse,
    status_code=201,
)
async def create_subject(
    agent_id: int,
    body: CreateSubjectRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_agent_or_404(agent_id, user, db)

    slug = _generate_slug(body.name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid subject name")

    workspace = Path(settings.data_dir) / user.username / "learning" / slug
    workspace.mkdir(parents=True, exist_ok=True)

    subject = LearningSubject(
        user_id=user.id,
        agent_id=agent_id,
        name=body.name,
        slug=slug,
        workspace_path=str(workspace),
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get(
    "/agents/{agent_id}/subjects",
    response_model=list[SubjectResponse],
)
async def list_subjects(
    agent_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_agent_or_404(agent_id, user, db)
    subjects = db.exec(
        select(LearningSubject).where(
            LearningSubject.agent_id == agent_id,
            LearningSubject.user_id == user.id,
        )
    ).all()
    return subjects


@router.get(
    "/subjects/{subject_id}",
    response_model=SubjectResponse,
)
async def get_subject(
    subject_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return _get_subject_or_404(subject_id, user, db)


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    subject = _get_subject_or_404(subject_id, user, db)

    # Delete all courses under this subject
    courses = db.exec(
        select(LearningCourse).where(
            LearningCourse.subject_id == subject.id,
        )
    ).all()
    for course in courses:
        # Delete chat messages for each course
        messages = db.exec(
            select(ChatMessage).where(
                ChatMessage.session_type == "learning",
                ChatMessage.session_id == course.id,
            )
        ).all()
        for msg in messages:
            db.delete(msg)
        db.delete(course)

    # Cleanup workspace directory
    workspace = Path(subject.workspace_path)
    if workspace.exists():
        shutil.rmtree(workspace)

    db.delete(subject)
    db.commit()
    return {"detail": "Subject deleted"}


# --- Course Endpoints ---


@router.post(
    "/subjects/{subject_id}/courses",
    response_model=CourseResponse,
    status_code=201,
)
async def create_course(
    subject_id: int,
    body: CreateCourseRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    subject = _get_subject_or_404(subject_id, user, db)

    slug = _generate_slug(body.name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid course name")

    course_dir = Path(subject.workspace_path) / slug
    course_dir.mkdir(parents=True, exist_ok=True)

    # Create empty chat_history.json
    chat_history_path = course_dir / "chat_history.json"
    chat_history_path.write_text("[]", encoding="utf-8")

    # Create empty student_notes.md
    student_notes_path = course_dir / "student_notes.md"
    student_notes_path.write_text("# Student Notes\n", encoding="utf-8")

    course = LearningCourse(
        user_id=user.id,
        subject_id=subject.id,
        name=body.name,
        slug=slug,
        instructions=body.instructions,
        chat_history_path=str(chat_history_path),
        student_notes_path=str(student_notes_path),
        workspace_path=str(course_dir),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get(
    "/subjects/{subject_id}/courses",
    response_model=list[CourseResponse],
)
async def list_courses(
    subject_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    subject = _get_subject_or_404(subject_id, user, db)
    courses = db.exec(
        select(LearningCourse).where(
            LearningCourse.subject_id == subject.id,
            LearningCourse.user_id == user.id,
        )
    ).all()
    return courses


@router.get(
    "/courses/{course_id}",
    response_model=CourseResponse,
)
async def get_course(
    course_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return _get_course_or_404(course_id, user, db)


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    course = _get_course_or_404(course_id, user, db)

    # Delete chat messages
    messages = db.exec(
        select(ChatMessage).where(
            ChatMessage.session_type == "learning",
            ChatMessage.session_id == course.id,
        )
    ).all()
    for msg in messages:
        db.delete(msg)

    # Cleanup workspace directory
    workspace = Path(course.workspace_path)
    if workspace.exists():
        shutil.rmtree(workspace)

    db.delete(course)
    db.commit()
    return {"detail": "Course deleted"}


# --- Chat Endpoints ---


@router.post(
    "/courses/{course_id}/message",
    response_model=ChatResponse,
    status_code=201,
)
async def send_message(
    course_id: int,
    body: SendMessageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    course = _get_course_or_404(course_id, user, db)

    # Load chat history from DB
    db_messages = db.exec(
        select(ChatMessage)
        .where(
            ChatMessage.session_type == "learning",
            ChatMessage.session_id == course.id,
        )
        .order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": m.role, "content": m.content} for m in db_messages]

    # Get the agent for identity
    subject = db.get(LearningSubject, course.subject_id)
    agent = db.get(Agent, subject.agent_id) if subject else None
    agent_identity = agent.identity if agent else ""

    # Read student notes
    student_notes = learning_agent.read_student_notes(course.student_notes_path)

    # Compose system prompt
    system_prompt = learning_agent.compose_system_prompt(
        agent_identity=agent_identity,
        course_instructions=course.instructions,
        student_notes=student_notes,
    )

    # Get AI response via ChatGPT subscription
    agent_model = agent.model if agent else "gpt-5.2"
    try:
        ai_response = await learning_agent.get_response(
            model=agent_model,
            system_prompt=system_prompt,
            messages=history,
            new_message=body.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Store user message
    user_msg = ChatMessage(
        user_id=user.id,
        session_type="learning",
        session_id=course.id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)

    # Store AI response
    assistant_msg = ChatMessage(
        user_id=user.id,
        session_type="learning",
        session_id=course.id,
        role="assistant",
        content=ai_response,
    )
    db.add(assistant_msg)

    db.commit()

    return {"message": ai_response}


@router.get(
    "/courses/{course_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    course_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    course = _get_course_or_404(course_id, user, db)

    messages = db.exec(
        select(ChatMessage)
        .where(
            ChatMessage.session_type == "learning",
            ChatMessage.session_id == course.id,
        )
        .order_by(ChatMessage.created_at)
    ).all()
    return messages
