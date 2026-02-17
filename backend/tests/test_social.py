"""Tests for social media API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.agent import Agent
from app.models.social import SocialAccount
from app.services.social_media import FacebookService, InstagramService


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def social_agent(session: Session, user_token: str, client: TestClient) -> dict:
    """Create a social_media agent for the test user."""
    resp = client.post(
        "/api/agents",
        json={"template": "social_media", "name": "My Social Agent"},
        headers=_auth(user_token),
    )
    return resp.json()


@pytest.fixture
def ig_account(session: Session, social_agent: dict) -> SocialAccount:
    """Create a test Instagram account linked to the social agent."""
    # Get user_id from the agent
    agent = session.get(Agent, social_agent["id"])
    account = SocialAccount(
        user_id=agent.user_id,
        agent_id=social_agent["id"],
        platform="instagram",
        access_token="test-ig-token",
        account_name="testuser_ig",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@pytest.fixture
def fb_account(session: Session, social_agent: dict) -> SocialAccount:
    """Create a test Facebook account linked to the social agent."""
    agent = session.get(Agent, social_agent["id"])
    account = SocialAccount(
        user_id=agent.user_id,
        agent_id=social_agent["id"],
        platform="facebook",
        access_token="test-fb-token",
        account_name="Test FB Page",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


# ==================== Connect / OAuth ====================


class TestConnectInstagram:
    def test_connect_instagram_returns_auth_url(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        resp = client.post(
            "/api/social/connect/instagram",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "state" in data
        assert "instagram.com/oauth/authorize" in data["auth_url"]
        assert "response_type=code" in data["auth_url"]

    def test_connect_instagram_with_agent_id(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        resp = client.post(
            f"/api/social/connect/instagram?agent_id={social_agent['id']}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert "auth_url" in resp.json()

    def test_connect_instagram_invalid_agent(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        resp = client.post(
            "/api/social/connect/instagram?agent_id=9999",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_connect_instagram_no_agent(
        self, client: TestClient, user_token: str
    ):
        """No social_media agent exists -> 404."""
        resp = client.post(
            "/api/social/connect/instagram",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404
        assert "No social media agent" in resp.json()["detail"]

    def test_connect_instagram_requires_auth(self, client: TestClient):
        resp = client.post("/api/social/connect/instagram")
        assert resp.status_code in [401, 403]


class TestConnectFacebook:
    def test_connect_facebook_returns_auth_url(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        resp = client.post(
            "/api/social/connect/facebook",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "state" in data
        assert "facebook.com" in data["auth_url"]
        assert "dialog/oauth" in data["auth_url"]

    def test_connect_facebook_no_agent(
        self, client: TestClient, user_token: str
    ):
        resp = client.post(
            "/api/social/connect/facebook",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_connect_facebook_requires_auth(self, client: TestClient):
        resp = client.post("/api/social/connect/facebook")
        assert resp.status_code in [401, 403]


class TestCallbackInstagram:
    def test_callback_instagram_success(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        """Test the full OAuth callback flow with mocked HTTP calls."""
        # Mock the token exchange and profile fetch
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "ig-access-token-123",
            "user_id": "12345",
        }

        mock_profile_response = MagicMock()
        mock_profile_response.status_code = 200
        mock_profile_response.json.return_value = {"username": "cool_user"}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_token_response
        mock_client_instance.get.return_value = mock_profile_response
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.social.httpx.AsyncClient", return_value=mock_client_instance):
            resp = client.get(
                "/api/social/callback/instagram?code=test-code&state=test-state",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["detail"] == "Instagram account connected"
        assert "account_id" in data

    def test_callback_instagram_token_exchange_fails(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.social.httpx.AsyncClient", return_value=mock_client_instance):
            resp = client.get(
                "/api/social/callback/instagram?code=bad-code&state=test-state",
                headers=_auth(user_token),
            )
        assert resp.status_code == 400
        assert "Failed to exchange" in resp.json()["detail"]

    def test_callback_instagram_requires_auth(self, client: TestClient):
        resp = client.get(
            "/api/social/callback/instagram?code=test&state=test"
        )
        assert resp.status_code in [401, 403]


class TestCallbackFacebook:
    def test_callback_facebook_success(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "fb-access-token-123",
        }

        mock_profile_response = MagicMock()
        mock_profile_response.status_code = 200
        mock_profile_response.json.return_value = {"name": "Test User"}

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=[mock_token_response, mock_profile_response]
        )
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.social.httpx.AsyncClient", return_value=mock_client_instance):
            resp = client.get(
                "/api/social/callback/facebook?code=fb-code&state=fb-state",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["detail"] == "Facebook account connected"
        assert "account_id" in data

    def test_callback_facebook_token_exchange_fails(
        self, client: TestClient, user_token: str, social_agent: dict
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.social.httpx.AsyncClient", return_value=mock_client_instance):
            resp = client.get(
                "/api/social/callback/facebook?code=bad&state=test",
                headers=_auth(user_token),
            )
        assert resp.status_code == 400


# ==================== Accounts ====================


class TestListAccounts:
    def test_list_accounts_empty(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/social/accounts",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_accounts_with_data(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
        fb_account: SocialAccount,
    ):
        resp = client.get(
            "/api/social/accounts",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        platforms = {a["platform"] for a in data}
        assert "instagram" in platforms
        assert "facebook" in platforms

    def test_list_accounts_no_access_token_in_response(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        """Ensure access_token is NOT exposed in the response."""
        resp = client.get(
            "/api/social/accounts",
            headers=_auth(user_token),
        )
        data = resp.json()
        assert len(data) == 1
        assert "access_token" not in data[0]

    def test_list_accounts_requires_auth(self, client: TestClient):
        resp = client.get("/api/social/accounts")
        assert resp.status_code in [401, 403]


class TestDisconnectAccount:
    def test_disconnect_account(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
        session: Session,
    ):
        resp = client.delete(
            f"/api/social/accounts/{ig_account.id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Account disconnected"

        # Verify account is gone
        account = session.get(SocialAccount, ig_account.id)
        assert account is None

    def test_disconnect_account_not_found(
        self, client: TestClient, user_token: str
    ):
        resp = client.delete(
            "/api/social/accounts/9999",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_disconnect_account_requires_auth(self, client: TestClient):
        resp = client.delete("/api/social/accounts/1")
        assert resp.status_code in [401, 403]


# ==================== User Isolation ====================


class TestUserIsolation:
    def test_cannot_list_other_users_accounts(
        self,
        client: TestClient,
        admin_token: str,
        user_token: str,
        ig_account: SocialAccount,
    ):
        """Admin should not see user's Instagram account."""
        resp = client.get(
            "/api/social/accounts",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        # Admin has no social accounts
        assert resp.json() == []

    def test_cannot_disconnect_other_users_account(
        self,
        client: TestClient,
        admin_token: str,
        ig_account: SocialAccount,
    ):
        resp = client.delete(
            f"/api/social/accounts/{ig_account.id}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 404


# ==================== Feed & Content ====================


class TestGetFeed:
    def test_get_feed_empty_no_accounts(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/social/feed",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json() == {"posts": []}

    def test_get_feed_with_instagram(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        mock_posts = [
            {"id": "1", "caption": "Hello", "media_type": "IMAGE"},
            {"id": "2", "caption": "World", "media_type": "VIDEO"},
        ]

        with patch(
            "app.api.social.InstagramService.get_media",
            new_callable=AsyncMock,
            return_value=mock_posts,
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ):
            resp = client.get(
                "/api/social/feed",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["posts"]) == 2
        assert data["posts"][0]["platform"] == "instagram"
        assert data["posts"][0]["account_name"] == "testuser_ig"

    def test_get_feed_with_both_platforms(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
        fb_account: SocialAccount,
    ):
        ig_posts = [{"id": "ig1", "caption": "IG post"}]
        fb_posts = [{"id": "fb1", "message": "FB post"}]

        with patch(
            "app.api.social.InstagramService.get_media",
            new_callable=AsyncMock,
            return_value=ig_posts,
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ), patch(
            "app.api.social.FacebookService.get_posts",
            new_callable=AsyncMock,
            return_value=fb_posts,
        ), patch(
            "app.api.social.FacebookService.close",
            new_callable=AsyncMock,
        ):
            resp = client.get(
                "/api/social/feed",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["posts"]) == 2
        platforms = {p["platform"] for p in data["posts"]}
        assert "instagram" in platforms
        assert "facebook" in platforms

    def test_get_feed_skips_failed_accounts(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        """If an API call fails, it should be skipped gracefully."""
        with patch(
            "app.api.social.InstagramService.get_media",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "401", request=MagicMock(), response=MagicMock()
            ),
        ):
            resp = client.get(
                "/api/social/feed",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        assert resp.json() == {"posts": []}

    def test_get_feed_requires_auth(self, client: TestClient):
        resp = client.get("/api/social/feed")
        assert resp.status_code in [401, 403]


class TestGetStories:
    def test_get_stories_no_accounts(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/social/stories",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json() == {"stories": []}

    def test_get_stories_with_data(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        mock_stories = [
            {"id": "s1", "media_type": "IMAGE", "timestamp": "2024-01-01"},
        ]

        with patch(
            "app.api.social.InstagramService.get_stories",
            new_callable=AsyncMock,
            return_value=mock_stories,
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ):
            resp = client.get(
                "/api/social/stories",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["stories"]) == 1
        assert data["stories"][0]["account_name"] == "testuser_ig"

    def test_get_stories_requires_auth(self, client: TestClient):
        resp = client.get("/api/social/stories")
        assert resp.status_code in [401, 403]


class TestPublishPost:
    def test_publish_to_instagram(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        with patch(
            "app.api.social.InstagramService.publish_post",
            new_callable=AsyncMock,
            return_value={"id": "new-ig-post-123"},
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                "/api/social/posts",
                json={
                    "platforms": ["instagram"],
                    "message": "Hello IG!",
                    "image_url": "https://example.com/photo.jpg",
                },
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["platform"] == "instagram"
        assert data["results"][0]["success"] is True

    def test_publish_to_facebook(
        self,
        client: TestClient,
        user_token: str,
        fb_account: SocialAccount,
    ):
        with patch(
            "app.api.social.FacebookService.publish_post",
            new_callable=AsyncMock,
            return_value={"id": "new-fb-post-456"},
        ), patch(
            "app.api.social.FacebookService.close",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                "/api/social/posts",
                json={
                    "platforms": ["facebook"],
                    "message": "Hello FB!",
                },
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["success"] is True

    def test_publish_to_both_platforms(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
        fb_account: SocialAccount,
    ):
        with patch(
            "app.api.social.InstagramService.publish_post",
            new_callable=AsyncMock,
            return_value={"id": "ig-123"},
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ), patch(
            "app.api.social.FacebookService.publish_post",
            new_callable=AsyncMock,
            return_value={"id": "fb-456"},
        ), patch(
            "app.api.social.FacebookService.close",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                "/api/social/posts",
                json={
                    "platforms": ["instagram", "facebook"],
                    "message": "Cross-post!",
                    "image_url": "https://example.com/img.jpg",
                },
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2
        assert all(r["success"] for r in data["results"])

    def test_publish_instagram_requires_image(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        resp = client.post(
            "/api/social/posts",
            json={
                "platforms": ["instagram"],
                "message": "No image!",
            },
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["success"] is False
        assert "image_url" in data["results"][0]["error"]

    def test_publish_no_account_connected(
        self, client: TestClient, user_token: str
    ):
        resp = client.post(
            "/api/social/posts",
            json={
                "platforms": ["instagram"],
                "message": "Test",
                "image_url": "https://example.com/img.jpg",
            },
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["success"] is False
        assert "No account connected" in data["results"][0]["error"]

    def test_publish_unsupported_platform(
        self, client: TestClient, user_token: str
    ):
        resp = client.post(
            "/api/social/posts",
            json={
                "platforms": ["tiktok"],
                "message": "Test",
            },
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["success"] is False

    def test_publish_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/social/posts",
            json={"platforms": ["instagram"], "message": "test"},
        )
        assert resp.status_code in [401, 403]


class TestGetComments:
    def test_get_comments_instagram(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        mock_comments = [
            {"id": "c1", "text": "Nice!", "username": "fan1"},
            {"id": "c2", "text": "Great post!", "username": "fan2"},
        ]

        with patch(
            "app.api.social.InstagramService.get_comments",
            new_callable=AsyncMock,
            return_value=mock_comments,
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ):
            resp = client.get(
                "/api/social/comments/post123?platform=instagram",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["comments"]) == 2

    def test_get_comments_facebook(
        self,
        client: TestClient,
        user_token: str,
        fb_account: SocialAccount,
    ):
        mock_comments = [{"id": "c1", "message": "Hello"}]

        with patch(
            "app.api.social.FacebookService.get_comments",
            new_callable=AsyncMock,
            return_value=mock_comments,
        ), patch(
            "app.api.social.FacebookService.close",
            new_callable=AsyncMock,
        ):
            resp = client.get(
                "/api/social/comments/post456?platform=facebook",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        assert len(resp.json()["comments"]) == 1

    def test_get_comments_no_account(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/social/comments/post123?platform=instagram",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_get_comments_requires_auth(self, client: TestClient):
        resp = client.get("/api/social/comments/post123?platform=instagram")
        assert resp.status_code in [401, 403]


class TestReplyToComment:
    def test_reply_instagram(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        with patch(
            "app.api.social.InstagramService.reply_to_comment",
            new_callable=AsyncMock,
            return_value={"id": "reply1"},
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                "/api/social/comments/comment123/reply?platform=instagram",
                json={"message": "Thanks!"},
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        assert "result" in resp.json()

    def test_reply_facebook(
        self,
        client: TestClient,
        user_token: str,
        fb_account: SocialAccount,
    ):
        with patch(
            "app.api.social.FacebookService.reply_to_comment",
            new_callable=AsyncMock,
            return_value={"id": "reply2"},
        ), patch(
            "app.api.social.FacebookService.close",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                "/api/social/comments/comment456/reply?platform=facebook",
                json={"message": "Thank you!"},
                headers=_auth(user_token),
            )
        assert resp.status_code == 200

    def test_reply_no_account(
        self, client: TestClient, user_token: str
    ):
        resp = client.post(
            "/api/social/comments/c1/reply?platform=instagram",
            json={"message": "Hey"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_reply_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/social/comments/c1/reply?platform=instagram",
            json={"message": "test"},
        )
        assert resp.status_code in [401, 403]


class TestGetDMs:
    def test_get_dms_with_account(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        mock_conversations = [
            {"id": "t1", "participants": {"data": [{"id": "u1"}]}},
        ]

        with patch(
            "app.api.social.InstagramService.get_conversations",
            new_callable=AsyncMock,
            return_value=mock_conversations,
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ):
            resp = client.get(
                "/api/social/dms",
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["conversations"]) == 1

    def test_get_dms_no_account(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/social/dms",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404
        assert "No Instagram account" in resp.json()["detail"]

    def test_get_dms_requires_auth(self, client: TestClient):
        resp = client.get("/api/social/dms")
        assert resp.status_code in [401, 403]


class TestReplyToDM:
    def test_reply_to_dm(
        self,
        client: TestClient,
        user_token: str,
        ig_account: SocialAccount,
    ):
        with patch(
            "app.api.social.InstagramService.send_message",
            new_callable=AsyncMock,
            return_value={"id": "msg123"},
        ), patch(
            "app.api.social.InstagramService.close",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                "/api/social/dms/thread1/reply",
                json={"message": "Hey there!"},
                headers=_auth(user_token),
            )
        assert resp.status_code == 200
        assert "result" in resp.json()

    def test_reply_to_dm_no_account(
        self, client: TestClient, user_token: str
    ):
        resp = client.post(
            "/api/social/dms/thread1/reply",
            json={"message": "Hello"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_reply_to_dm_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/social/dms/thread1/reply",
            json={"message": "test"},
        )
        assert resp.status_code in [401, 403]


# ==================== AI Assistant ====================


class TestAIChat:
    def test_ai_chat_returns_placeholder(
        self, client: TestClient, user_token: str
    ):
        resp = client.post(
            "/api/social/ai/chat",
            json={"message": "Write a caption for my sunset photo"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert "social media AI assistant" in data["reply"]
        assert "coming soon" in data["reply"].lower()

    def test_ai_chat_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/social/ai/chat",
            json={"message": "test"},
        )
        assert resp.status_code in [401, 403]


# ==================== Service Unit Tests ====================


class TestInstagramService:
    @pytest.mark.asyncio
    async def test_get_media(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "1", "caption": "Test"}]
        }
        mock_response.raise_for_status = MagicMock()

        svc = InstagramService("test-token")
        svc.client = AsyncMock()
        svc.client.get.return_value = mock_response

        result = await svc.get_media()
        assert len(result) == 1
        assert result[0]["id"] == "1"
        svc.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stories(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "s1", "media_type": "IMAGE"}]
        }
        mock_response.raise_for_status = MagicMock()

        svc = InstagramService("test-token")
        svc.client = AsyncMock()
        svc.client.get.return_value = mock_response

        result = await svc.get_stories()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_publish_post(self):
        container_response = MagicMock()
        container_response.json.return_value = {"id": "container-1"}
        container_response.raise_for_status = MagicMock()

        publish_response = MagicMock()
        publish_response.json.return_value = {"id": "post-1"}
        publish_response.raise_for_status = MagicMock()

        svc = InstagramService("test-token")
        svc.client = AsyncMock()
        svc.client.post.side_effect = [container_response, publish_response]

        result = await svc.publish_post("https://img.url/photo.jpg", "Caption")
        assert result["id"] == "post-1"
        assert svc.client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_comments(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "c1", "text": "Nice!"}]
        }
        mock_response.raise_for_status = MagicMock()

        svc = InstagramService("test-token")
        svc.client = AsyncMock()
        svc.client.get.return_value = mock_response

        result = await svc.get_comments("media123")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_reply_to_comment(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "reply1"}
        mock_response.raise_for_status = MagicMock()

        svc = InstagramService("test-token")
        svc.client = AsyncMock()
        svc.client.post.return_value = mock_response

        result = await svc.reply_to_comment("c1", "Thanks!")
        assert result["id"] == "reply1"

    @pytest.mark.asyncio
    async def test_get_conversations(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "t1"}]}
        mock_response.raise_for_status = MagicMock()

        svc = InstagramService("test-token")
        svc.client = AsyncMock()
        svc.client.get.return_value = mock_response

        result = await svc.get_conversations()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_send_message(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "msg1"}
        mock_response.raise_for_status = MagicMock()

        svc = InstagramService("test-token")
        svc.client = AsyncMock()
        svc.client.post.return_value = mock_response

        result = await svc.send_message("t1", "Hello!")
        assert result["id"] == "msg1"


class TestFacebookService:
    @pytest.mark.asyncio
    async def test_get_posts(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "p1", "message": "Hello FB"}]
        }
        mock_response.raise_for_status = MagicMock()

        svc = FacebookService("test-token", page_id="page123")
        svc.client = AsyncMock()
        svc.client.get.return_value = mock_response

        result = await svc.get_posts()
        assert len(result) == 1
        assert result[0]["message"] == "Hello FB"

    @pytest.mark.asyncio
    async def test_publish_post_text_only(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "post-new"}
        mock_response.raise_for_status = MagicMock()

        svc = FacebookService("test-token", page_id="page123")
        svc.client = AsyncMock()
        svc.client.post.return_value = mock_response

        result = await svc.publish_post("Hello world!")
        assert result["id"] == "post-new"
        # Should call the feed endpoint (no image)
        call_args = svc.client.post.call_args
        assert "feed" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_publish_post_with_image(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "photo-new"}
        mock_response.raise_for_status = MagicMock()

        svc = FacebookService("test-token", page_id="page123")
        svc.client = AsyncMock()
        svc.client.post.return_value = mock_response

        result = await svc.publish_post("Check this!", "https://img.url/photo.jpg")
        assert result["id"] == "photo-new"
        # Should call the photos endpoint
        call_args = svc.client.post.call_args
        assert "photos" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_comments(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "c1", "message": "Great!"}]
        }
        mock_response.raise_for_status = MagicMock()

        svc = FacebookService("test-token")
        svc.client = AsyncMock()
        svc.client.get.return_value = mock_response

        result = await svc.get_comments("post123")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_reply_to_comment(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "reply1"}
        mock_response.raise_for_status = MagicMock()

        svc = FacebookService("test-token")
        svc.client = AsyncMock()
        svc.client.post.return_value = mock_response

        result = await svc.reply_to_comment("c1", "Thanks!")
        assert result["id"] == "reply1"

    @pytest.mark.asyncio
    async def test_get_posts_default_target(self):
        """When no page_id, should use 'me' as target."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        svc = FacebookService("test-token")
        svc.client = AsyncMock()
        svc.client.get.return_value = mock_response

        await svc.get_posts()
        call_args = svc.client.get.call_args
        assert "/me/feed" in call_args[0][0]
