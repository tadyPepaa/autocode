"""Tests for settings API endpoints — API key management."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.common import ApiKey


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==================== List API Keys ====================


class TestListApiKeys:
    def test_list_empty(self, client: TestClient, user_token: str):
        resp = client.get("/api/settings/api-keys", headers=_auth(user_token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_adding(self, client: TestClient, user_token: str):
        client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-test-key-12345678"},
            headers=_auth(user_token),
        )
        resp = client.get("/api/settings/api-keys", headers=_auth(user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["provider"] == "openai"
        assert data[0]["masked_key"].endswith("5678")
        assert "sk-test-key" not in data[0]["masked_key"]

    def test_list_requires_auth(self, client: TestClient):
        resp = client.get("/api/settings/api-keys")
        assert resp.status_code in [401, 403]


# ==================== Add/Update API Keys ====================


class TestAddApiKey:
    def test_add_key(self, client: TestClient, user_token: str):
        resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-abc123def456"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["masked_key"].endswith("f456")
        assert "id" in data
        assert "created_at" in data

    def test_add_key_anthropic(self, client: TestClient, user_token: str):
        resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "anthropic", "key": "sk-ant-secret-key-9999"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        assert resp.json()["provider"] == "anthropic"
        assert resp.json()["masked_key"].endswith("9999")

    def test_update_existing_key(
        self, client: TestClient, user_token: str, session: Session
    ):
        """Adding a key for an existing provider should update, not duplicate."""
        client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-old-key-AAAA"},
            headers=_auth(user_token),
        )
        resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-new-key-BBBB"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        assert resp.json()["masked_key"].endswith("BBBB")

        # Only one key for openai
        keys = client.get(
            "/api/settings/api-keys", headers=_auth(user_token)
        ).json()
        openai_keys = [k for k in keys if k["provider"] == "openai"]
        assert len(openai_keys) == 1

    def test_add_unsupported_provider(self, client: TestClient, user_token: str):
        resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "unsupported_provider", "key": "some-key"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 400
        assert "Unsupported provider" in resp.json()["detail"]

    def test_add_empty_key(self, client: TestClient, user_token: str):
        resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": ""},
            headers=_auth(user_token),
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_add_whitespace_key(self, client: TestClient, user_token: str):
        resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "   "},
            headers=_auth(user_token),
        )
        assert resp.status_code == 400

    def test_add_key_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-test"},
        )
        assert resp.status_code in [401, 403]

    def test_add_multiple_providers(self, client: TestClient, user_token: str):
        client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-openai-key"},
            headers=_auth(user_token),
        )
        client.post(
            "/api/settings/api-keys",
            json={"provider": "anthropic", "key": "sk-ant-key"},
            headers=_auth(user_token),
        )
        resp = client.get("/api/settings/api-keys", headers=_auth(user_token))
        assert len(resp.json()) == 2
        providers = {k["provider"] for k in resp.json()}
        assert providers == {"openai", "anthropic"}


# ==================== Delete API Keys ====================


class TestDeleteApiKey:
    def test_delete_key(self, client: TestClient, user_token: str):
        add_resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-to-delete"},
            headers=_auth(user_token),
        )
        key_id = add_resp.json()["id"]

        resp = client.delete(
            f"/api/settings/api-keys/{key_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "API key deleted"

        # Verify it's gone
        keys = client.get(
            "/api/settings/api-keys", headers=_auth(user_token)
        ).json()
        assert len(keys) == 0

    def test_delete_nonexistent_key(self, client: TestClient, user_token: str):
        resp = client.delete(
            "/api/settings/api-keys/9999",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_delete_requires_auth(self, client: TestClient):
        resp = client.delete("/api/settings/api-keys/1")
        assert resp.status_code in [401, 403]


# ==================== User Isolation ====================


class TestUserIsolation:
    def test_cannot_see_other_users_keys(
        self, client: TestClient, user_token: str, admin_token: str
    ):
        """User's keys should not be visible to admin."""
        client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-user-secret"},
            headers=_auth(user_token),
        )

        resp = client.get(
            "/api/settings/api-keys", headers=_auth(admin_token)
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_cannot_delete_other_users_key(
        self, client: TestClient, user_token: str, admin_token: str
    ):
        add_resp = client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-user-only"},
            headers=_auth(user_token),
        )
        key_id = add_resp.json()["id"]

        resp = client.delete(
            f"/api/settings/api-keys/{key_id}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 404


# ==================== Key Masking ====================


class TestKeyMasking:
    def test_short_key_fully_masked(self, client: TestClient, user_token: str):
        """Keys with 4 or fewer chars should be fully masked."""
        client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "abc"},
            headers=_auth(user_token),
        )
        resp = client.get("/api/settings/api-keys", headers=_auth(user_token))
        data = resp.json()
        assert data[0]["masked_key"] == "****"

    def test_normal_key_shows_last_4(self, client: TestClient, user_token: str):
        client.post(
            "/api/settings/api-keys",
            json={"provider": "openai", "key": "sk-1234567890abcdef"},
            headers=_auth(user_token),
        )
        resp = client.get("/api/settings/api-keys", headers=_auth(user_token))
        data = resp.json()
        assert data[0]["masked_key"].endswith("cdef")
        assert data[0]["masked_key"].startswith("*")
        # Full key should NOT appear
        assert "sk-1234567890" not in data[0]["masked_key"]
