import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.models.agent import Agent
from app.models.common import ChatMessage
from app.models.research import ResearchSession


@pytest.fixture
def data_dir(tmp_path):
    """Override settings.data_dir to use tmp_path for tests."""
    original = settings.data_dir
    settings.data_dir = str(tmp_path)
    yield tmp_path
    settings.data_dir = original


@pytest.fixture
def agent(session: Session, user_token: str, client: TestClient) -> dict:
    """Create a research agent and return its data."""
    resp = client.post(
        "/api/agents",
        json={"template": "research", "name": "Test Research Agent"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    return resp.json()


@pytest.fixture
def mock_claude():
    """Mock run_claude_message for tests that involve Claude CLI."""
    with patch("app.api.research.run_claude_message", new_callable=AsyncMock) as mock:
        mock.return_value = "Claude response"
        yield mock


def _create_research(
    client: TestClient,
    user_token: str,
    agent_id: int,
    name: str = "My Research Topic",
) -> dict:
    resp = client.post(
        f"/api/agents/{agent_id}/research",
        json={"name": name},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    return resp


# --- Create research session tests ---


def test_create_research_session(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    resp = _create_research(
        client, user_token, agent["id"], name="Deep Learning Research"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Deep Learning Research"
    assert data["slug"] == "deep-learning-research"
    assert data["status"] == "idle"
    assert data["agent_id"] == agent["id"]

    # Verify workspace was created with CLAUDE.md
    workspace = Path(data["workspace_path"])
    assert workspace.exists()
    claude_md = workspace / "CLAUDE.md"
    assert claude_md.exists()


def test_create_research_slug_generation(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    resp = _create_research(
        client, user_token, agent["id"], name="Hello World! @#$ Research"
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "hello-world-research"


def test_create_research_invalid_name(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    resp = _create_research(client, user_token, agent["id"], name="@#$%")
    assert resp.status_code == 400
    assert "Invalid session name" in resp.json()["detail"]


def test_create_research_invalid_agent(
    client: TestClient,
    user_token: str,
    data_dir: Path,
):
    resp = _create_research(client, user_token, 9999, name="Bad")
    assert resp.status_code == 404


def test_create_research_workspace_path(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    resp = _create_research(client, user_token, agent["id"], name="Neural Nets")
    data = resp.json()
    expected = str(data_dir / "testuser" / "research" / "neural-nets")
    assert data["workspace_path"] == expected


def test_create_research_writes_claude_md(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    # Update agent identity first
    client.put(
        f"/api/agents/{agent['id']}",
        json={"identity": "You are a research expert."},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    resp = _create_research(client, user_token, agent["id"], name="Identity Test")
    workspace = Path(resp.json()["workspace_path"])
    claude_md = workspace / "CLAUDE.md"
    assert claude_md.exists()
    assert "research expert" in claude_md.read_text()


# --- List research sessions tests ---


def test_list_research_sessions(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    _create_research(client, user_token, agent["id"], name="Topic One")
    _create_research(client, user_token, agent["id"], name="Topic Two")

    resp = client.get(
        f"/api/agents/{agent['id']}/research",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {s["name"] for s in data}
    assert "Topic One" in names
    assert "Topic Two" in names


def test_list_research_sessions_empty(
    client: TestClient,
    user_token: str,
    agent: dict,
):
    resp = client.get(
        f"/api/agents/{agent['id']}/research",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_research_invalid_agent(
    client: TestClient,
    user_token: str,
):
    resp = client.get(
        "/api/agents/9999/research",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Get research session detail tests ---


def test_get_research_session(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Detail Test"
    )
    session_id = create_resp.json()["id"]

    resp = client.get(
        f"/api/research/{session_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == session_id
    assert data["name"] == "Detail Test"


def test_get_research_session_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.get(
        "/api/research/9999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Delete research session tests ---


def test_delete_research_session(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Delete Me"
    )
    session_id = create_resp.json()["id"]
    workspace_path = create_resp.json()["workspace_path"]

    assert Path(workspace_path).exists()

    resp = client.delete(
        f"/api/research/{session_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Research session deleted"

    # Verify workspace cleaned up
    assert not Path(workspace_path).exists()

    # Verify session is gone
    resp = client.get(
        f"/api/research/{session_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


def test_delete_research_session_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.delete(
        "/api/research/9999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


def test_delete_research_cleans_chat_messages(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    session: Session,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Msg Cleanup"
    )
    session_id = create_resp.json()["id"]

    # Add messages directly to DB (avoid background task timing issues)
    msg = ChatMessage(
        user_id=2,
        session_type="research",
        session_id=session_id,
        role="user",
        content="Hello Claude",
    )
    session.add(msg)
    session.commit()

    # Verify message exists
    messages = session.exec(
        select(ChatMessage).where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == session_id,
        )
    ).all()
    assert len(messages) == 1

    # Delete session
    client.delete(
        f"/api/research/{session_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Verify messages cleaned up
    messages = session.exec(
        select(ChatMessage).where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == session_id,
        )
    ).all()
    assert len(messages) == 0


# --- Send message tests ---


def test_send_message(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_claude,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Chat Session"
    )
    session_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/research/{session_id}/message",
        json={"content": "What is transformer architecture?"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "What is transformer architecture?"
    assert data["status"] == "thinking"
    assert "id" in data


def test_send_message_stores_user_msg_in_db(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_claude,
    session: Session,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="DB Chat"
    )
    session_id = create_resp.json()["id"]

    client.post(
        f"/api/research/{session_id}/message",
        json={"content": "Test message"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # User message is stored synchronously before background task
    messages = session.exec(
        select(ChatMessage).where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == session_id,
        )
    ).all()
    assert len(messages) >= 1
    assert messages[0].role == "user"
    assert messages[0].content == "Test message"

    # Verify Claude was called
    mock_claude.assert_called_once()
    call_kwargs = mock_claude.call_args
    assert call_kwargs[1]["message"] == "Test message" or call_kwargs[0][1] == "Test message"


def test_send_message_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.post(
        "/api/research/9999/message",
        json={"content": "Hello"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


def test_send_message_sets_thinking_status(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_claude,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Thinking Test"
    )
    session_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/research/{session_id}/message",
        json={"content": "Think about this"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.json()["status"] == "thinking"


# --- Cancel tests ---


def test_cancel_research(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Cancel Me"
    )
    session_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/research/{session_id}/cancel",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_cancel_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.post(
        "/api/research/9999/cancel",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Messages endpoint tests ---


def test_get_research_messages(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    session: Session,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Messages")
    session_id = create_resp.json()["id"]

    for role, content in [
        ("user", "What is AI?"),
        ("assistant", "AI is artificial intelligence."),
        ("user", "Tell me more"),
    ]:
        msg = ChatMessage(
            user_id=2,
            session_type="research",
            session_id=session_id,
            role=role,
            content=content,
        )
        session.add(msg)
    session.commit()

    resp = client.get(
        f"/api/research/{session_id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "What is AI?"


def test_get_research_messages_empty(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Empty")
    session_id = create_resp.json()["id"]

    resp = client.get(
        f"/api/research/{session_id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_research_messages_not_found(client: TestClient, user_token: str):
    resp = client.get(
        "/api/research/9999/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Files endpoint tests ---


def test_list_research_files(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Files Test")
    workspace = Path(create_resp.json()["workspace_path"])
    (workspace / "research.md").write_text("# Research\n\nSome content")
    (workspace / "notes.md").write_text("# Notes")
    (workspace / "data.csv").write_text("a,b,c")

    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/files",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    names = {f["name"] for f in data}
    assert "research.md" in names
    assert "notes.md" in names
    assert "data.csv" not in names


def test_list_research_files_empty(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(client, user_token, agent["id"], name="No Extra Files")
    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/files",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_research_file_content(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Content Test")
    workspace = Path(create_resp.json()["workspace_path"])
    (workspace / "output.md").write_text("# Output\n\nHello world")

    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/file-content",
        params={"path": "output.md"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "# Output\n\nHello world"
    assert data["name"] == "output.md"


def test_get_research_file_content_traversal_blocked(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Traversal")
    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/file-content",
        params={"path": "../../etc/passwd"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 400


def test_get_research_file_content_not_found(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Missing")
    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/file-content",
        params={"path": "nonexistent.md"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- User isolation tests ---


def test_cannot_access_other_users_research(
    client: TestClient,
    user_token: str,
    admin_token: str,
    data_dir: Path,
):
    # Create agent as admin
    agent_resp = client.post(
        "/api/agents",
        json={"template": "research", "name": "Admin Research Agent"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_agent_id = agent_resp.json()["id"]

    # Create research session as admin
    create_resp = _create_research(
        client, admin_token, admin_agent_id, name="Admin Only Research"
    )
    session_id = create_resp.json()["id"]

    # User tries to get it
    resp = client.get(
        f"/api/research/{session_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404

    # User tries to delete it
    resp = client.delete(
        f"/api/research/{session_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404

    # User tries to send message
    resp = client.post(
        f"/api/research/{session_id}/message",
        json={"content": "Hacked"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404

    # User tries to cancel
    resp = client.post(
        f"/api/research/{session_id}/cancel",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


def test_cannot_list_other_users_research(
    client: TestClient,
    user_token: str,
    admin_token: str,
    data_dir: Path,
):
    # Admin creates agent
    agent_resp = client.post(
        "/api/agents",
        json={"template": "research", "name": "Admin Agent"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_agent_id = agent_resp.json()["id"]

    # Admin creates research session
    _create_research(
        client, admin_token, admin_agent_id, name="Secret Research"
    )

    # User tries to list admin's agent research — should get 404
    resp = client.get(
        f"/api/agents/{admin_agent_id}/research",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Auth required tests ---


def test_create_research_requires_auth(
    client: TestClient,
    agent: dict,
):
    resp = client.post(
        f"/api/agents/{agent['id']}/research",
        json={"name": "No Auth"},
    )
    assert resp.status_code in [401, 403]


def test_list_research_requires_auth(
    client: TestClient,
    agent: dict,
):
    resp = client.get(f"/api/agents/{agent['id']}/research")
    assert resp.status_code in [401, 403]
