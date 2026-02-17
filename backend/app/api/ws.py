import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.database import engine
from app.models.common import Log
from app.models.project import Project
from app.services.tmux import TmuxManager

router = APIRouter()
tmux = TmuxManager()


@router.websocket("/ws/project/{project_id}/terminal")
async def project_terminal(websocket: WebSocket, project_id: int):
    """Stream tmux pane content to frontend for xterm.js display."""
    await websocket.accept()

    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            await websocket.close(code=4004)
            return
        tmux_session = project.tmux_session

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


@router.websocket("/ws/project/{project_id}/logs")
async def project_logs(websocket: WebSocket, project_id: int):
    """Stream project logs."""
    await websocket.accept()
    last_id = 0
    try:
        while True:
            with Session(engine) as session:
                logs = session.exec(
                    select(Log)
                    .where(Log.project_id == project_id, Log.id > last_id)
                    .order_by(Log.id)
                ).all()
                for log in logs:
                    await websocket.send_json(
                        {
                            "id": log.id,
                            "level": log.level,
                            "message": log.message,
                            "timestamp": str(log.timestamp),
                        }
                    )
                    last_id = log.id
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
