import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.models.agent import Agent
from app.models.user import User


@pytest.fixture
def data_dir(tmp_path):
    """Override settings.data_dir to use tmp_path for tests."""
    original = settings.data_dir
    settings.data_dir = str(tmp_path)
    yield tmp_path
    settings.data_dir = original


@pytest.fixture
def agent(session: Session, user_token: str, client: TestClient) -> dict:
    """Create a coding agent and return its data."""
    resp = client.post(
        "/api/agents",
        json={"template": "coding", "name": "Test Coding Agent"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    return resp.json()


@pytest.fixture
def mock_tmux():
    """Mock TmuxManager for tests that involve tmux operations."""
    with patch("app.api.projects.tmux") as mock:
        mock.create_session = MagicMock()
        mock.kill_session = MagicMock()
        mock.send_keys = MagicMock()
        mock.session_exists = MagicMock(return_value=False)
        mock.capture_pane = MagicMock(return_value="")
        yield mock


def _create_project(
    client: TestClient,
    user_token: str,
    agent_id: int,
    name: str = "My Test Project",
    description: str = "A test project",
    architecture: str | None = None,
) -> dict:
    body = {"name": name, "description": description}
    if architecture is not None:
        body["architecture"] = architecture
    resp = client.post(
        f"/api/agents/{agent_id}/projects",
        json=body,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    return resp


# --- Create project tests ---


def test_create_project(
    client: TestClient, user_token: str, agent: dict, data_dir: Path
):
    resp = _create_project(
        client,
        user_token,
        agent["id"],
        name="My Awesome Project",
        description="Building something cool",
        architecture="React + FastAPI",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Awesome Project"
    assert data["slug"] == "my-awesome-project"
    assert data["description"] == "Building something cool"
    assert data["architecture"] == "React + FastAPI"
    assert data["status"] == "created"
    assert data["agent_id"] == agent["id"]
    assert "testuser" in data["tmux_session"]

    # Verify workspace was created
    workspace = Path(data["workspace_path"])
    assert workspace.exists()
    assert (workspace / ".claude" / "CLAUDE.md").exists()
    assert (workspace / ".nanobot" / "IDENTITY.md").exists()

    # Verify CLAUDE.md content
    claude_md = (workspace / ".claude" / "CLAUDE.md").read_text()
    assert "My Awesome Project" in claude_md
    assert "Building something cool" in claude_md
    assert "React + FastAPI" in claude_md

    # Verify IDENTITY.md content
    identity = (workspace / ".nanobot" / "IDENTITY.md").read_text()
    assert "My Awesome Project" in identity


def test_create_project_slug_generation(
    client: TestClient, user_token: str, agent: dict, data_dir: Path
):
    resp = _create_project(
        client,
        user_token,
        agent["id"],
        name="Hello World! @#$ Test",
        description="Slug test",
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "hello-world-test"


def test_create_project_without_architecture(
    client: TestClient, user_token: str, agent: dict, data_dir: Path
):
    resp = _create_project(
        client,
        user_token,
        agent["id"],
        name="Simple Project",
        description="No arch",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["architecture"] == ""


def test_create_project_invalid_agent(
    client: TestClient, user_token: str, data_dir: Path
):
    resp = _create_project(client, user_token, 9999, name="Bad", description="Fail")
    assert resp.status_code == 404


# --- List projects tests ---


def test_list_projects(
    client: TestClient, user_token: str, agent: dict, data_dir: Path
):
    _create_project(client, user_token, agent["id"], name="Project One", description="P1")
    _create_project(client, user_token, agent["id"], name="Project Two", description="P2")

    resp = client.get(
        f"/api/agents/{agent['id']}/projects",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {p["name"] for p in data}
    assert "Project One" in names
    assert "Project Two" in names


def test_list_projects_empty(
    client: TestClient, user_token: str, agent: dict
):
    resp = client.get(
        f"/api/agents/{agent['id']}/projects",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# --- Get project detail tests ---


def test_get_project_detail(
    client: TestClient, user_token: str, agent: dict, data_dir: Path
):
    create_resp = _create_project(
        client, user_token, agent["id"], name="Detail Test", description="Desc"
    )
    project_id = create_resp.json()["id"]

    resp = client.get(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == project_id
    assert data["name"] == "Detail Test"


def test_get_project_not_found(client: TestClient, user_token: str):
    resp = client.get(
        "/api/projects/9999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Update project tests ---


def test_update_project(
    client: TestClient, user_token: str, agent: dict, data_dir: Path
):
    create_resp = _create_project(
        client, user_token, agent["id"], name="Update Me", description="Old"
    )
    project_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/projects/{project_id}",
        json={"description": "New description", "architecture": "New arch"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "New description"
    assert data["architecture"] == "New arch"
    assert data["name"] == "Update Me"  # unchanged


def test_update_project_partial(
    client: TestClient, user_token: str, agent: dict, data_dir: Path
):
    create_resp = _create_project(
        client,
        user_token,
        agent["id"],
        name="Partial",
        description="Original",
        architecture="React",
    )
    project_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/projects/{project_id}",
        json={"description": "Updated"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Updated"
    assert data["architecture"] == "React"  # unchanged


# --- Delete project tests ---


def test_delete_project(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_project(
        client, user_token, agent["id"], name="Delete Me", description="Gone"
    )
    project_id = create_resp.json()["id"]
    workspace_path = create_resp.json()["workspace_path"]

    assert Path(workspace_path).exists()

    resp = client.delete(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Project deleted"

    # Verify workspace cleaned up
    assert not Path(workspace_path).exists()

    # Verify tmux kill was called
    mock_tmux.kill_session.assert_called()

    # Verify project is gone
    resp = client.get(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# --- Start project tests ---


def test_start_project(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_project(
        client, user_token, agent["id"], name="Start Me", description="Go"
    )
    project_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/projects/{project_id}/start",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"

    # Verify tmux was called
    mock_tmux.create_session.assert_called_once()
    mock_tmux.send_keys.assert_called_once()

    # Verify claude command was sent
    call_args = mock_tmux.send_keys.call_args
    assert call_args[0][1] == "claude"


def test_start_already_running_project(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_project(
        client, user_token, agent["id"], name="Running", description="Already"
    )
    project_id = create_resp.json()["id"]

    # Start once
    client.post(
        f"/api/projects/{project_id}/start",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Start again - should fail
    resp = client.post(
        f"/api/projects/{project_id}/start",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 400
    assert "already running" in resp.json()["detail"]


# --- Stop project tests ---


def test_stop_project(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_project(
        client, user_token, agent["id"], name="Stop Me", description="Halt"
    )
    project_id = create_resp.json()["id"]

    # Start first
    client.post(
        f"/api/projects/{project_id}/start",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Stop
    resp = client.post(
        f"/api/projects/{project_id}/stop",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "paused"

    # Verify tmux kill was called
    mock_tmux.kill_session.assert_called()


# --- Restart project tests ---


def test_restart_project(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_project(
        client, user_token, agent["id"], name="Restart Me", description="Again"
    )
    project_id = create_resp.json()["id"]

    # Start first
    client.post(
        f"/api/projects/{project_id}/start",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Restart
    resp = client.post(
        f"/api/projects/{project_id}/restart",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"

    # tmux should have been called: kill + create + send_keys
    assert mock_tmux.kill_session.call_count >= 1
    assert mock_tmux.create_session.call_count >= 2  # start + restart
    assert mock_tmux.send_keys.call_count >= 2  # start + restart


# --- Access control tests ---


def test_cannot_access_other_users_project(
    client: TestClient,
    user_token: str,
    admin_token: str,
    data_dir: Path,
):
    # Create agent as admin
    agent_resp = client.post(
        "/api/agents",
        json={"template": "coding", "name": "Admin Agent"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_agent_id = agent_resp.json()["id"]

    # Create project as admin
    create_resp = _create_project(
        client, admin_token, admin_agent_id, name="Admin Only", description="Secret"
    )
    project_id = create_resp.json()["id"]

    # User tries to access
    resp = client.get(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404

    # User tries to update
    resp = client.put(
        f"/api/projects/{project_id}",
        json={"description": "Hacked"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404

    # User tries to delete
    resp = client.delete(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404
