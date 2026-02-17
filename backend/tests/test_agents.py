import pytest
from fastapi.testclient import TestClient


def test_create_agent_from_template(client: TestClient, user_token: str):
    response = client.post(
        "/api/agents",
        json={"template": "coding", "name": "My Coding Agent"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Coding Agent"
    assert data["type"] == "coding"
    assert data["model"] == "gpt-5.2-codex"
    assert "coding agent" in data["identity"].lower()
    assert data["user_id"] is not None


def test_create_agent_from_unknown_template(client: TestClient, user_token: str):
    response = client.post(
        "/api/agents",
        json={"template": "nonexistent", "name": "Bad Agent"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 400
    assert "Unknown template" in response.json()["detail"]


def test_create_custom_agent(client: TestClient, user_token: str):
    response = client.post(
        "/api/agents",
        json={
            "name": "Custom Bot",
            "type": "custom",
            "model": "openai/gpt-4o",
            "identity": "You are a helpful assistant.",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Custom Bot"
    assert data["type"] == "custom"
    assert data["model"] == "openai/gpt-4o"
    assert data["identity"] == "You are a helpful assistant."


def test_create_custom_agent_missing_fields(client: TestClient, user_token: str):
    response = client.post(
        "/api/agents",
        json={"name": "Incomplete"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 400
    assert "type and model" in response.json()["detail"]


def test_list_agents_only_own(client: TestClient, user_token: str, admin_token: str):
    # User creates an agent
    client.post(
        "/api/agents",
        json={"template": "research", "name": "User Research"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    # Admin creates an agent
    client.post(
        "/api/agents",
        json={"template": "coding", "name": "Admin Coding"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # User sees only their agent
    response = client.get(
        "/api/agents",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "User Research"

    # Admin sees only their agent
    response = client.get(
        "/api/agents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Admin Coding"


def test_get_agent_detail(client: TestClient, user_token: str):
    create_resp = client.post(
        "/api/agents",
        json={"template": "learning", "name": "My Tutor"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    agent_id = create_resp.json()["id"]

    response = client.get(
        f"/api/agents/{agent_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == agent_id
    assert data["name"] == "My Tutor"
    assert data["type"] == "learning"


def test_update_agent(client: TestClient, user_token: str):
    create_resp = client.post(
        "/api/agents",
        json={"template": "coding", "name": "Original"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    agent_id = create_resp.json()["id"]

    response = client.put(
        f"/api/agents/{agent_id}",
        json={"name": "Updated Name", "model": "anthropic/claude-opus-4-6"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["model"] == "anthropic/claude-opus-4-6"
    # Unchanged fields stay the same
    assert data["type"] == "coding"


def test_delete_agent(client: TestClient, user_token: str):
    create_resp = client.post(
        "/api/agents",
        json={"template": "social_media", "name": "Social Bot"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    agent_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/agents/{agent_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["detail"] == "Agent deleted"

    # Verify it's gone
    response = client.get(
        f"/api/agents/{agent_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404


def test_get_templates(client: TestClient, user_token: str):
    response = client.get(
        "/api/agents/templates",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "coding" in data
    assert "research" in data
    assert "learning" in data
    assert "social_media" in data
    assert data["coding"]["model"] == "gpt-5.2-codex"


def test_get_available_models(client: TestClient, user_token: str):
    response = client.get(
        "/api/agents/models",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all("id" in m and "name" in m and "category" in m for m in data)
    model_ids = [m["id"] for m in data]
    assert "gpt-5.2-codex" in model_ids
    assert "gpt-5.2" in model_ids


def test_init_default_agents(client: TestClient, user_token: str):
    # First call creates all 4 default agents
    response = client.post(
        "/api/agents/init",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data["created"]) == {"coding", "research", "learning", "social_media"}

    # Second call creates nothing (idempotent)
    response = client.post(
        "/api/agents/init",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == []

    # Verify agents exist
    response = client.get(
        "/api/agents",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    types = {a["type"] for a in response.json()}
    assert "coding" in types
    assert "research" in types
    assert "learning" in types
    assert "social_media" in types


def test_cannot_access_other_users_agent(
    client: TestClient, user_token: str, admin_token: str
):
    # Admin creates an agent
    create_resp = client.post(
        "/api/agents",
        json={"template": "coding", "name": "Admin Only"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    agent_id = create_resp.json()["id"]

    # User tries to get it
    response = client.get(
        f"/api/agents/{agent_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404

    # User tries to update it
    response = client.put(
        f"/api/agents/{agent_id}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404

    # User tries to delete it
    response = client.delete(
        f"/api/agents/{agent_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404
