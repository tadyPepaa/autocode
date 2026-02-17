import asyncio
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.config import settings
from app.database import engine, get_session
from app.models.agent import Agent
from app.models.common import ChatMessage
from app.models.research import ResearchSession
from app.models.user import User
from app.services.tmux import TmuxManager

router = APIRouter(tags=["research"])

tmux = TmuxManager()


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
    _get_agent_or_404(agent_id, user, db)

    slug = _generate_slug(body.name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid session name")

    workspace = Path(settings.data_dir) / user.username / "research" / slug
    workspace.mkdir(parents=True, exist_ok=True)

    tmux_session = f"{user.username}-research-{slug}"

    # Create tmux session and start claude (skip permission prompts)
    tmux.create_session(tmux_session, str(workspace))
    tmux.send_keys(tmux_session, "claude --dangerously-skip-permissions")

    research = ResearchSession(
        user_id=user.id,
        agent_id=agent_id,
        name=body.name,
        slug=slug,
        status="active",
        tmux_session=tmux_session,
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


@router.delete("/research/{session_id}")
async def delete_research_session(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    # Kill tmux session if it exists
    if research.tmux_session:
        tmux.kill_session(research.tmux_session)

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

    # Store message in chat_messages
    message = ChatMessage(
        user_id=user.id,
        session_type="research",
        session_id=research.id,
        role="user",
        content=body.content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Send to Claude Code via tmux
    tmux.send_keys(research.tmux_session, body.content)

    return {
        "id": message.id,
        "content": body.content,
        "status": "sent",
    }


@router.post(
    "/research/{session_id}/resume",
    response_model=ResearchSessionResponse,
)
async def resume_research_session(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    if not tmux.session_exists(research.tmux_session):
        # Create new tmux session and resume claude
        workspace = Path(research.workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)
        tmux.create_session(research.tmux_session, str(workspace))
        tmux.send_keys(
            research.tmux_session,
            "claude --dangerously-skip-permissions --resume",
        )

    research.status = "active"
    research.updated_at = datetime.utcnow()
    db.add(research)
    db.commit()
    db.refresh(research)
    return research


@router.post(
    "/research/{session_id}/stop",
    response_model=ResearchSessionResponse,
)
async def stop_research_session(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    if research.tmux_session:
        tmux.kill_session(research.tmux_session)

    research.status = "stopped"
    research.updated_at = datetime.utcnow()
    db.add(research)
    db.commit()
    db.refresh(research)
    return research


# --- WebSocket ---


@router.websocket("/ws/research/{session_id}/terminal")
async def research_terminal(websocket: WebSocket, session_id: int):
    """Stream tmux pane content for research session terminal."""
    await websocket.accept()

    with Session(engine) as db:
        research = db.get(ResearchSession, session_id)
        if not research:
            await websocket.close(code=4004)
            return
        tmux_session = research.tmux_session

    try:
        last_output = ""
        while True:
            if tmux.session_exists(tmux_session):
                output = tmux.capture_pane(tmux_session)
                if output != last_output:
                    await websocket.send_text(output)
                    last_output = output
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
