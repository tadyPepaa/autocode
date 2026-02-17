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
from app.models.common import AgentInstance
from app.models.project import Project
from app.models.user import User
from app.services.tmux import TmuxManager

router = APIRouter(tags=["projects"])

tmux = TmuxManager()


def _generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a project name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _setup_workspace(
    workspace: Path,
    project_name: str,
    description: str,
    architecture: str,
    agent: Agent,
) -> None:
    """Create workspace directories and config files."""
    workspace.mkdir(parents=True, exist_ok=True)

    # Create .claude/CLAUDE.md
    claude_dir = workspace / ".claude"
    claude_dir.mkdir(exist_ok=True)
    claude_md_content = f"# {project_name}\n\n{description}\n"
    if architecture:
        claude_md_content += f"\n## Architecture\n\n{architecture}\n"
    (claude_dir / "CLAUDE.md").write_text(claude_md_content)

    # Create .nanobot/ directory with config
    nanobot_dir = workspace / ".nanobot"
    nanobot_dir.mkdir(exist_ok=True)

    identity_content = ""
    if agent.global_rules:
        identity_content += f"# Global Rules\n\n{agent.global_rules}\n\n"
    identity_content += f"# Project: {project_name}\n\n{description}\n"
    if architecture:
        identity_content += f"\n## Architecture\n\n{architecture}\n"
    (nanobot_dir / "IDENTITY.md").write_text(identity_content)


# --- Pydantic models ---


class CreateProjectRequest(BaseModel):
    name: str
    description: str
    architecture: str | None = None


class UpdateProjectRequest(BaseModel):
    description: str | None = None
    architecture: str | None = None


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    agent_id: int
    name: str
    slug: str
    description: str
    architecture: str
    implementation_plan: str
    status: str
    current_step: int
    tmux_session: str
    workspace_path: str
    created_at: datetime
    updated_at: datetime


# --- Helpers ---


def _get_project_or_404(
    project_id: int, user: User, session: Session
) -> Project:
    project = session.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_agent_or_404(
    agent_id: int, user: User, session: Session
) -> Agent:
    agent = session.get(Agent, agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# --- Endpoints ---


@router.get(
    "/agents/{agent_id}/projects", response_model=list[ProjectResponse]
)
async def list_projects(
    agent_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_agent_or_404(agent_id, user, session)
    projects = session.exec(
        select(Project).where(
            Project.agent_id == agent_id, Project.user_id == user.id
        )
    ).all()
    return projects


@router.post(
    "/agents/{agent_id}/projects",
    response_model=ProjectResponse,
    status_code=201,
)
async def create_project(
    agent_id: int,
    body: CreateProjectRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agent = _get_agent_or_404(agent_id, user, session)

    slug = _generate_slug(body.name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid project name")

    workspace = Path(settings.data_dir) / user.username / "projects" / slug
    tmux_session = f"{user.username}-{slug}"

    _setup_workspace(
        workspace,
        body.name,
        body.description,
        body.architecture or "",
        agent,
    )

    project = Project(
        user_id=user.id,
        agent_id=agent_id,
        name=body.name,
        slug=slug,
        description=body.description,
        architecture=body.architecture or "",
        tmux_session=tmux_session,
        workspace_path=str(workspace),
        status="created",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return _get_project_or_404(project_id, user, session)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    body: UpdateProjectRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, user, session)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, user, session)

    # Kill tmux session if it exists
    if project.tmux_session:
        tmux.kill_session(project.tmux_session)

    # Cleanup workspace
    workspace = Path(project.workspace_path)
    if workspace.exists():
        shutil.rmtree(workspace)

    # Delete related agent instances
    instances = session.exec(
        select(AgentInstance).where(AgentInstance.project_id == project.id)
    ).all()
    for instance in instances:
        session.delete(instance)

    session.delete(project)
    session.commit()
    return {"detail": "Project deleted"}


@router.post("/projects/{project_id}/start", response_model=ProjectResponse)
async def start_project(
    project_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, user, session)

    if project.status == "running":
        raise HTTPException(status_code=400, detail="Project is already running")

    # Create tmux session
    workspace = Path(project.workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)
    tmux.create_session(project.tmux_session, str(workspace))

    # Send claude command to start Claude Code
    tmux.send_keys(project.tmux_session, "claude")

    # Create AgentInstance record
    instance = AgentInstance(
        user_id=user.id,
        agent_id=project.agent_id,
        project_id=project.id,
        pid=None,
        status="running",
        started_at=datetime.utcnow(),
    )
    session.add(instance)

    # Update project status
    project.status = "running"
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.post("/projects/{project_id}/stop", response_model=ProjectResponse)
async def stop_project(
    project_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, user, session)

    # Kill tmux session
    if project.tmux_session:
        tmux.kill_session(project.tmux_session)

    # Update running agent instances
    instances = session.exec(
        select(AgentInstance).where(
            AgentInstance.project_id == project.id,
            AgentInstance.status == "running",
        )
    ).all()
    for instance in instances:
        instance.status = "stopped"
        instance.stopped_at = datetime.utcnow()
        session.add(instance)

    # Update project status
    project.status = "paused"
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.post(
    "/projects/{project_id}/restart", response_model=ProjectResponse
)
async def restart_project(
    project_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, user, session)

    # Stop first: kill tmux session
    if project.tmux_session:
        tmux.kill_session(project.tmux_session)

    # Stop running agent instances
    instances = session.exec(
        select(AgentInstance).where(
            AgentInstance.project_id == project.id,
            AgentInstance.status == "running",
        )
    ).all()
    for instance in instances:
        instance.status = "stopped"
        instance.stopped_at = datetime.utcnow()
        session.add(instance)

    # Start: create tmux session
    workspace = Path(project.workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)
    tmux.create_session(project.tmux_session, str(workspace))

    # Send claude command
    tmux.send_keys(project.tmux_session, "claude")

    # Create new AgentInstance
    new_instance = AgentInstance(
        user_id=user.id,
        agent_id=project.agent_id,
        project_id=project.id,
        pid=None,
        status="running",
        started_at=datetime.utcnow(),
    )
    session.add(new_instance)

    # Update project status
    project.status = "running"
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project
