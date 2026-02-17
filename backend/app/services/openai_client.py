"""OpenAI client using ChatGPT subscription tokens from Codex CLI auth."""

import json
from pathlib import Path

import httpx
from openai import AsyncOpenAI

CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
REFRESH_URL = "https://auth.openai.com/oauth/token"


def _read_auth() -> dict:
    """Read auth tokens from ~/.codex/auth.json."""
    if not CODEX_AUTH_PATH.exists():
        raise ValueError(
            "No Codex auth found. Run 'codex' and login with ChatGPT first."
        )
    return json.loads(CODEX_AUTH_PATH.read_text())


def _write_auth(auth: dict) -> None:
    """Write updated tokens back to ~/.codex/auth.json."""
    CODEX_AUTH_PATH.write_text(json.dumps(auth, indent=2))


async def _refresh_tokens(refresh_token: str) -> dict:
    """Refresh access token using ChatGPT OAuth refresh token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            REFRESH_URL,
            json={
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "openid profile email",
            },
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_chatgpt_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client using ChatGPT subscription tokens.

    Reads tokens from ~/.codex/auth.json (shared with Codex CLI).
    Refreshes the access token if needed.
    """
    auth = _read_auth()
    tokens = auth.get("tokens", {})
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    account_id = tokens.get("account_id")

    if not access_token or not refresh_token:
        raise ValueError(
            "No ChatGPT tokens found. Run 'codex' and login first."
        )

    # Try to refresh token to ensure it's fresh
    try:
        refreshed = await _refresh_tokens(refresh_token)
        if refreshed.get("access_token"):
            access_token = refreshed["access_token"]
            tokens["access_token"] = access_token
        if refreshed.get("refresh_token"):
            tokens["refresh_token"] = refreshed["refresh_token"]
        if refreshed.get("id_token"):
            tokens["id_token"] = refreshed["id_token"]
        auth["tokens"] = tokens
        _write_auth(auth)
    except httpx.HTTPStatusError:
        # Use existing token, it might still be valid
        pass

    # Create client with ChatGPT subscription token
    client = AsyncOpenAI(
        api_key=access_token,
        default_headers={
            "chatgpt-account-id": account_id or "",
        },
    )
    return client
