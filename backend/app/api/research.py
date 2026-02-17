import asyncio
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.config import settings
from app.database import engine, get_session
from app.models.agent import Agent
from app.models.common import ChatMessage
from app.models.research import ResearchSession
from app.models.user import User
from app.services.research_runner import run_claude_message

router = APIRouter(tags=["research"])

# Track running background tasks by session_id for cancellation
_running_tasks: dict[int, asyncio.Task] = {}


def _generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# --- Pydantic models ---


class CreateResearchRequest(BaseModel):
    name: str


class SendMessageRequest(BaseModel):
    content: str


class ResearchSessionResponse(BaseModel):
    id: int
    user_id: int
    agent_id: int
    name: str
    slug: str
    status: str
    tmux_session: str
    workspace_path: str
    created_at: datetime
    updated_at: datetime


class SendMessageResponse(BaseModel):
    id: int
    content: str
    status: str


class MessageResponse(BaseModel):
    id: int
    user_id: int
    session_type: str
    session_id: int
    role: str
    content: str
    created_at: datetime


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    modified_at: float


class FileContent(BaseModel):
    name: str
    path: str
    content: str


class UpdateResearchRequest(BaseModel):
    name: str


# --- Helpers ---


def _get_session_or_404(
    session_id: int, user: User, db: Session
) -> ResearchSession:
    research = db.get(ResearchSession, session_id)
    if not research or research.user_id != user.id:
        raise HTTPException(status_code=404, detail="Research session not found")
    return research


def _get_agent_or_404(
    agent_id: int, user: User, db: Session
) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def _process_claude_response(
    session_id: int,
    user_id: int,
    workspace_path: str,
    user_message: str,
    is_continuation: bool,
) -> None:
    """Background task: run Claude CLI and store response."""
    with Session(engine) as db:
        try:
            response_text = await run_claude_message(
                workspace_path=workspace_path,
                message=user_message,
                is_continuation=is_continuation,
            )

            assistant_msg = ChatMessage(
                user_id=user_id,
                session_type="research",
                session_id=session_id,
                role="assistant",
                content=response_text,
            )
            db.add(assistant_msg)

        except Exception as e:
            error_msg = ChatMessage(
                user_id=user_id,
                session_type="research",
                session_id=session_id,
                role="assistant",
                content=f"Error: {str(e)}",
            )
            db.add(error_msg)

        finally:
            research = db.get(ResearchSession, session_id)
            if research:
                research.status = "idle"
                research.updated_at = datetime.utcnow()
                db.add(research)
            db.commit()
            _running_tasks.pop(session_id, None)


# --- Endpoints ---


@router.get(
    "/agents/{agent_id}/research",
    response_model=list[ResearchSessionResponse],
)
async def list_research_sessions(
    agent_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_agent_or_404(agent_id, user, db)
    sessions = db.exec(
        select(ResearchSession).where(
            ResearchSession.agent_id == agent_id,
            ResearchSession.user_id == user.id,
        )
    ).all()
    return sessions


@router.post(
    "/agents/{agent_id}/research",
    response_model=ResearchSessionResponse,
    status_code=201,
)
async def create_research_session(
    agent_id: int,
    body: CreateResearchRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agent = _get_agent_or_404(agent_id, user, db)

    slug = _generate_slug(body.name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid session name")

    workspace = Path(settings.data_dir) / user.username / "research" / slug
    workspace.mkdir(parents=True, exist_ok=True)

    # Write agent identity to CLAUDE.md
    claude_md = workspace / "CLAUDE.md"
    identity = agent.identity or "You are a research assistant."
    claude_md.write_text(identity, encoding="utf-8")

    research = ResearchSession(
        user_id=user.id,
        agent_id=agent_id,
        name=body.name,
        slug=slug,
        status="idle",
        tmux_session="",
        workspace_path=str(workspace),
    )
    db.add(research)
    db.commit()
    db.refresh(research)
    return research


@router.get(
    "/research/{session_id}",
    response_model=ResearchSessionResponse,
)
async def get_research_session(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return _get_session_or_404(session_id, user, db)


@router.put(
    "/research/{session_id}",
    response_model=ResearchSessionResponse,
)
async def update_research_session(
    session_id: int,
    body: UpdateResearchRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)
    research.name = body.name
    db.add(research)
    db.commit()
    db.refresh(research)
    return research


@router.delete("/research/{session_id}")
async def delete_research_session(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    # Cancel running task if exists
    task = _running_tasks.get(research.id)
    if task and not task.done():
        task.cancel()
        _running_tasks.pop(research.id, None)

    # Cleanup workspace
    workspace = Path(research.workspace_path)
    if workspace.exists():
        shutil.rmtree(workspace)

    # Delete related chat messages
    messages = db.exec(
        select(ChatMessage).where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == research.id,
        )
    ).all()
    for msg in messages:
        db.delete(msg)

    db.delete(research)
    db.commit()
    return {"detail": "Research session deleted"}


@router.post(
    "/research/{session_id}/message",
    response_model=SendMessageResponse,
    status_code=201,
)
async def send_message(
    session_id: int,
    body: SendMessageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    # Check if already has messages (for continuation flag)
    existing_count = len(
        db.exec(
            select(ChatMessage).where(
                ChatMessage.session_type == "research",
                ChatMessage.session_id == research.id,
            )
        ).all()
    )

    # Store user message
    message = ChatMessage(
        user_id=user.id,
        session_type="research",
        session_id=research.id,
        role="user",
        content=body.content,
    )
    db.add(message)

    # Update status to thinking
    research.status = "thinking"
    research.updated_at = datetime.utcnow()
    db.add(research)
    db.commit()
    db.refresh(message)

    # Launch background task
    task = asyncio.create_task(
        _process_claude_response(
            session_id=research.id,
            user_id=user.id,
            workspace_path=research.workspace_path,
            user_message=body.content,
            is_continuation=existing_count > 0,
        )
    )
    _running_tasks[research.id] = task

    return {
        "id": message.id,
        "content": body.content,
        "status": "thinking",
    }


@router.post(
    "/research/{session_id}/cancel",
    response_model=ResearchSessionResponse,
)
async def cancel_research(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    # Cancel running task if exists
    task = _running_tasks.get(research.id)
    if task and not task.done():
        task.cancel()
        _running_tasks.pop(research.id, None)

    research.status = "idle"
    research.updated_at = datetime.utcnow()
    db.add(research)
    db.commit()
    db.refresh(research)
    return research


# --- Read endpoints ---


@router.get(
    "/research/{session_id}/messages",
    response_model=list[MessageResponse],
)
async def get_research_messages(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_session_or_404(session_id, user, db)
    messages = db.exec(
        select(ChatMessage)
        .where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.created_at)
    ).all()
    return messages


@router.get(
    "/research/{session_id}/files",
    response_model=list[FileInfo],
)
async def list_research_files(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)
    workspace = Path(research.workspace_path)
    if not workspace.exists():
        return []

    files = []
    for md_file in sorted(workspace.rglob("*.md")):
        # Skip hidden dirs like .claude/
        if any(part.startswith(".") for part in md_file.relative_to(workspace).parts):
            continue
        stat = md_file.stat()
        files.append(FileInfo(
            name=md_file.name,
            path=str(md_file.relative_to(workspace)),
            size=stat.st_size,
            modified_at=stat.st_mtime,
        ))
    files.sort(key=lambda f: f.modified_at, reverse=True)
    return files


@router.get(
    "/research/{session_id}/file-content",
    response_model=FileContent,
)
async def get_research_file_content(
    session_id: int,
    path: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)
    workspace = Path(research.workspace_path)
    target = (workspace / path).resolve()

    if not str(target).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    content = target.read_text(encoding="utf-8")
    return FileContent(name=target.name, path=path, content=content)
