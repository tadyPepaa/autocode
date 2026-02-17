from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.agent import Agent
from app.models.user import User
from app.services.agent_templates import TEMPLATES, get_template, list_templates

router = APIRouter(prefix="/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    template: str | None = None
    name: str
    type: str | None = None
    model: str | None = None
    identity: str | None = None
    tools: str | None = None
    mcp_servers: str | None = None
    global_rules: str | None = None


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    model: str | None = None
    identity: str | None = None
    tools: str | None = None
    mcp_servers: str | None = None
    global_rules: str | None = None


class AgentResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: str
    model: str
    identity: str
    tools: str
    mcp_servers: str
    global_rules: str
    created_at: datetime


@router.get("/templates")
async def get_templates():
    return {name: TEMPLATES[name] for name in list_templates()}


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agents = session.exec(
        select(Agent).where(Agent.user_id == user.id)
    ).all()
    return agents


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if body.template:
        tmpl = get_template(body.template)
        if not tmpl:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown template: {body.template}",
            )
        agent = Agent(
            user_id=user.id,
            name=body.name,
            type=tmpl["type"],
            model=tmpl["model"],
            identity=tmpl["identity"],
            tools=tmpl["tools"],
            global_rules=tmpl["global_rules"],
        )
    else:
        if not body.type or not body.model:
            raise HTTPException(
                status_code=400,
                detail="Custom agent requires type and model",
            )
        agent = Agent(
            user_id=user.id,
            name=body.name,
            type=body.type,
            model=body.model,
            identity=body.identity or "",
            tools=body.tools or "[]",
            mcp_servers=body.mcp_servers or "[]",
            global_rules=body.global_rules or "",
        )

    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agent = session.get(Agent, agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    body: UpdateAgentRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agent = session.get(Agent, agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agent = session.get(Agent, agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")

    session.delete(agent)
    session.commit()
    return {"detail": "Agent deleted"}
