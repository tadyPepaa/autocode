from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

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
def mock_tmux():
    """Mock TmuxManager for tests that involve tmux operations."""
    with patch("app.api.research.tmux") as mock:
        mock.create_session = MagicMock()
        mock.kill_session = MagicMock()
        mock.send_keys = MagicMock()
        mock.session_exists = MagicMock(return_value=False)
        mock.capture_pane = MagicMock(return_value="")
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
    mock_tmux,
):
    resp = _create_research(
        client, user_token, agent["id"], name="Deep Learning Research"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Deep Learning Research"
    assert data["slug"] == "deep-learning-research"
    assert data["status"] == "active"
    assert data["agent_id"] == agent["id"]
    assert "testuser" in data["tmux_session"]
    assert "research" in data["tmux_session"]

    # Verify workspace was created
    workspace = Path(data["workspace_path"])
    assert workspace.exists()

    # Verify tmux session was created and claude started
    mock_tmux.create_session.assert_called_once()
    mock_tmux.send_keys.assert_called_once()
    call_args = mock_tmux.send_keys.call_args
    assert call_args[0][1] == "claude"


def test_create_research_slug_generation(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
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
    mock_tmux,
):
    resp = _create_research(client, user_token, agent["id"], name="@#$%")
    assert resp.status_code == 400
    assert "Invalid session name" in resp.json()["detail"]


def test_create_research_invalid_agent(
    client: TestClient,
    user_token: str,
    data_dir: Path,
    mock_tmux,
):
    resp = _create_research(client, user_token, 9999, name="Bad")
    assert resp.status_code == 404


def test_create_research_tmux_naming(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    resp = _create_research(client, user_token, agent["id"], name="AI Safety")
    data = resp.json()
    assert data["tmux_session"] == "testuser-research-ai-safety"


def test_create_research_workspace_path(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    resp = _create_research(client, user_token, agent["id"], name="Neural Nets")
    data = resp.json()
    expected = str(data_dir / "testuser" / "research" / "neural-nets")
    assert data["workspace_path"] == expected


# --- List research sessions tests ---


def test_list_research_sessions(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
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
    mock_tmux,
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
    mock_tmux,
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

    # Verify tmux kill was called
    mock_tmux.kill_session.assert_called()

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
    mock_tmux,
    session: Session,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Msg Cleanup"
    )
    session_id = create_resp.json()["id"]

    # Send a message
    client.post(
        f"/api/research/{session_id}/message",
        json={"content": "Hello Claude"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Verify message exists
    from sqlmodel import select

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
    mock_tmux,
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
    assert data["status"] == "sent"
    assert "id" in data

    # Verify tmux send_keys was called (create + message)
    assert mock_tmux.send_keys.call_count == 2
    last_call = mock_tmux.send_keys.call_args_list[-1]
    assert last_call[0][1] == "What is transformer architecture?"


def test_send_message_stores_in_db(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
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

    from sqlmodel import select

    messages = session.exec(
        select(ChatMessage).where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == session_id,
        )
    ).all()
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "Test message"


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


# --- Resume tests ---


def test_resume_research_session(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Resume Me"
    )
    session_id = create_resp.json()["id"]

    # Stop first
    client.post(
        f"/api/research/{session_id}/stop",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # tmux.session_exists returns False (session was killed)
    mock_tmux.session_exists.return_value = False

    resp = client.post(
        f"/api/research/{session_id}/resume",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"

    # Verify tmux was recreated and claude --resume was sent
    # create_session called twice: initial create + resume
    assert mock_tmux.create_session.call_count == 2
    last_send = mock_tmux.send_keys.call_args_list[-1]
    assert last_send[0][1] == "claude --resume"


def test_resume_already_running(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Still Running"
    )
    session_id = create_resp.json()["id"]

    # tmux session still exists
    mock_tmux.session_exists.return_value = True

    resp = client.post(
        f"/api/research/{session_id}/resume",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"

    # Should NOT create a new tmux session (only 1 from initial create)
    assert mock_tmux.create_session.call_count == 1


def test_resume_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.post(
        "/api/research/9999/resume",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Stop tests ---


def test_stop_research_session(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(
        client, user_token, agent["id"], name="Stop Me"
    )
    session_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/research/{session_id}/stop",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "stopped"

    # Verify tmux kill was called
    mock_tmux.kill_session.assert_called()


def test_stop_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.post(
        "/api/research/9999/stop",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- User isolation tests ---


def test_cannot_access_other_users_research(
    client: TestClient,
    user_token: str,
    admin_token: str,
    data_dir: Path,
    mock_tmux,
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

    # User tries to resume
    resp = client.post(
        f"/api/research/{session_id}/resume",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404

    # User tries to stop
    resp = client.post(
        f"/api/research/{session_id}/stop",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


def test_cannot_list_other_users_research(
    client: TestClient,
    user_token: str,
    admin_token: str,
    data_dir: Path,
    mock_tmux,
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

    # User tries to list admin's agent research - should get 404 (not their agent)
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
