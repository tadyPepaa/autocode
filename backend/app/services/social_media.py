"""Social media services for Instagram and Facebook Graph API integration."""

import httpx


class InstagramService:
    """Service for Instagram Graph API operations."""

    BASE_URL = "https://graph.instagram.com/v22.0"

    def __init__(self, access_token: str):
        self.token = access_token
        self.client = httpx.AsyncClient()

    async def get_media(self) -> list:
        """Get media posts from the authenticated Instagram account."""
        resp = await self.client.get(
            f"{self.BASE_URL}/me/media",
            params={
                "fields": "id,caption,media_type,media_url,thumbnail_url,timestamp,permalink",
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def get_stories(self) -> list:
        """Get stories from the authenticated Instagram account."""
        resp = await self.client.get(
            f"{self.BASE_URL}/me/stories",
            params={
                "fields": "id,media_type,media_url,timestamp",
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def publish_post(self, image_url: str, caption: str) -> dict:
        """Publish a photo post to Instagram (container-based publishing)."""
        # Step 1: Create media container
        container_resp = await self.client.post(
            f"{self.BASE_URL}/me/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.token,
            },
        )
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        # Step 2: Publish the container
        publish_resp = await self.client.post(
            f"{self.BASE_URL}/me/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self.token,
            },
        )
        publish_resp.raise_for_status()
        return publish_resp.json()

    async def get_comments(self, media_id: str) -> list:
        """Get comments for a specific media post."""
        resp = await self.client.get(
            f"{self.BASE_URL}/{media_id}/comments",
            params={
                "fields": "id,text,username,timestamp",
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def reply_to_comment(self, comment_id: str, message: str) -> dict:
        """Reply to a specific comment."""
        resp = await self.client.post(
            f"{self.BASE_URL}/{comment_id}/replies",
            params={
                "message": message,
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def get_conversations(self) -> list:
        """Get DM conversations from Instagram."""
        resp = await self.client.get(
            f"{self.BASE_URL}/me/conversations",
            params={
                "platform": "instagram",
                "fields": "id,participants,messages{id,message,from,created_time}",
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def send_message(self, thread_id: str, message: str) -> dict:
        """Send a message in a DM thread."""
        resp = await self.client.post(
            f"{self.BASE_URL}/{thread_id}/messages",
            params={
                "message": message,
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class FacebookService:
    """Service for Facebook Graph API operations."""

    BASE_URL = "https://graph.facebook.com/v22.0"

    def __init__(self, access_token: str, page_id: str = ""):
        self.token = access_token
        self.page_id = page_id
        self.client = httpx.AsyncClient()

    async def get_posts(self) -> list:
        """Get posts from the Facebook page."""
        target = self.page_id or "me"
        resp = await self.client.get(
            f"{self.BASE_URL}/{target}/feed",
            params={
                "fields": "id,message,created_time,full_picture,permalink_url,type",
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def publish_post(
        self, message: str, image_url: str | None = None
    ) -> dict:
        """Publish a post to the Facebook page."""
        target = self.page_id or "me"
        params: dict = {
            "message": message,
            "access_token": self.token,
        }
        if image_url:
            endpoint = f"{self.BASE_URL}/{target}/photos"
            params["url"] = image_url
        else:
            endpoint = f"{self.BASE_URL}/{target}/feed"

        resp = await self.client.post(endpoint, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_comments(self, post_id: str) -> list:
        """Get comments for a specific post."""
        resp = await self.client.get(
            f"{self.BASE_URL}/{post_id}/comments",
            params={
                "fields": "id,message,from,created_time",
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def reply_to_comment(self, comment_id: str, message: str) -> dict:
        """Reply to a specific comment."""
        resp = await self.client.post(
            f"{self.BASE_URL}/{comment_id}/comments",
            params={
                "message": message,
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
