"""ChatGPT subscription client using Codex CLI OAuth tokens.

Uses the ChatGPT backend Responses API (streaming) instead of the
standard OpenAI API, as subscription tokens don't have API access.
"""

import json
from pathlib import Path

import httpx

CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
REFRESH_URL = "https://auth.openai.com/oauth/token"
RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


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


async def _get_auth_headers() -> dict[str, str]:
    """Get fresh auth headers for ChatGPT API."""
    auth = _read_auth()
    tokens = auth.get("tokens", {})
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    account_id = tokens.get("account_id")

    if not access_token or not refresh_token:
        raise ValueError(
            "No ChatGPT tokens found. Run 'codex' and login first."
        )

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
        pass

    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "chatgpt-account-id": account_id or "",
    }


async def chatgpt_response(
    model: str,
    instructions: str,
    messages: list[dict[str, str]],
) -> str:
    """Send a request to ChatGPT Responses API and return the text.

    Args:
        model: Model ID (e.g. "gpt-5.3-codex", "gpt-5.2")
        instructions: System prompt / instructions
        messages: List of {"role": "user"|"assistant", "content": "..."}

    Returns:
        The assistant's response text.
    """
    headers = await _get_auth_headers()

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            RESPONSES_URL,
            headers=headers,
            json={
                "model": model,
                "instructions": instructions,
                "input": messages,
                "store": False,
                "stream": True,
            },
            timeout=120.0,
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise ValueError(
                    f"ChatGPT API error ({resp.status_code}): {body.decode()[:200]}"
                )

            collected_text = ""
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    if event.get("type") == "response.output_text.delta":
                        collected_text += event.get("delta", "")
                    if event.get("type") == "error":
                        raise ValueError(
                            f"ChatGPT stream error: {event.get('message', 'unknown')}"
                        )
                except json.JSONDecodeError:
                    continue

    return collected_text
