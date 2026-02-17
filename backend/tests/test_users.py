from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _override_data_dir(tmp_path, monkeypatch):
    """Use a temp directory for workspace creation/deletion during tests."""
    monkeypatch.setattr("app.config.settings.data_dir", str(tmp_path))


def test_create_user(client, admin_token, tmp_path):
    response = client.post(
        "/api/users",
        json={"username": "testcreate", "password": "pass123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testcreate"
    assert "password_hash" not in data
    assert "id" in data

    # Verify workspace directories were created
    user_dir = tmp_path / "testcreate"
    for subdir in ("projects", "research", "learning", "config"):
        assert (user_dir / subdir).is_dir()


def test_list_users(client, admin_token):
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 1
    # Ensure no password hashes leak
    for u in users:
        assert "password_hash" not in u


def test_delete_user(client, admin_token, tmp_path):
    # Create user first
    client.post(
        "/api/users",
        json={"username": "todelete", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Verify workspace exists
    assert (tmp_path / "todelete" / "projects").is_dir()

    # Find user id
    users = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    uid = [u for u in users if u["username"] == "todelete"][0]["id"]

    # Delete
    response = client.delete(
        f"/api/users/{uid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    # Verify workspace removed
    assert not (tmp_path / "todelete").exists()

    # Verify user gone from list
    users = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    assert all(u["username"] != "todelete" for u in users)


def test_non_admin_cannot_manage_users(client, user_token):
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_create_duplicate_user(client, admin_token):
    client.post(
        "/api/users",
        json={"username": "dupuser", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = client.post(
        "/api/users",
        json={"username": "dupuser", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


def test_delete_nonexistent_user(client, admin_token):
    response = client.delete(
        "/api/users/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
