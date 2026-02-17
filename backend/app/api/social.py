"""Social media API endpoints for Instagram and Facebook integration."""

import hashlib
import secrets
from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models.agent import Agent
from app.models.social import SocialAccount
from app.models.user import User
from app.services.social_media import FacebookService, InstagramService

router = APIRouter(prefix="/social", tags=["social"])


# --- Pydantic models ---


class SocialAccountResponse(BaseModel):
    id: int
    user_id: int
    agent_id: int
    platform: str
    account_name: str
    created_at: datetime


class OAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class OAuthCallbackResponse(BaseModel):
    detail: str
    account_id: int


class PublishPostRequest(BaseModel):
    platforms: list[str]  # ["instagram", "facebook"]
    message: str
    image_url: str | None = None


class PublishPostResponse(BaseModel):
    results: list[dict]


class ReplyRequest(BaseModel):
    message: str


class AIChatRequest(BaseModel):
    message: str


class AIChatResponse(BaseModel):
    reply: str


# --- Helpers ---


def _generate_state(user_id: int) -> str:
    """Generate a CSRF state token for OAuth."""
    raw = f"{user_id}-{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_user_social_agent(user: User, db: Session) -> Agent:
    """Find or raise 404 for the user's social_media agent."""
    agent = db.exec(
        select(Agent).where(
            Agent.user_id == user.id,
            Agent.type == "social_media",
        )
    ).first()
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="No social media agent found. Create one first.",
        )
    return agent


def _get_account_or_404(
    account_id: int, user: User, db: Session
) -> SocialAccount:
    account = db.get(SocialAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Social account not found")
    return account


# --- Account management ---


@router.post("/connect/instagram", response_model=OAuthUrlResponse)
async def connect_instagram(
    agent_id: int | None = Query(default=None),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Initiate Instagram OAuth flow. Returns the authorization URL."""
    if agent_id:
        agent = db.get(Agent, agent_id)
        if not agent or agent.user_id != user.id:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        _get_user_social_agent(user, db)

    state = _generate_state(user.id)
    params = {
        "client_id": settings.instagram_app_id,
        "redirect_uri": f"{settings.app_base_url}/api/social/callback/instagram",
        "scope": "instagram_basic,instagram_content_publish,instagram_manage_comments,instagram_manage_messages",
        "response_type": "code",
        "state": state,
    }
    auth_url = f"https://www.instagram.com/oauth/authorize?{urlencode(params)}"
    return OAuthUrlResponse(auth_url=auth_url, state=state)


@router.get("/callback/instagram", response_model=OAuthCallbackResponse)
async def callback_instagram(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Handle Instagram OAuth callback. Exchange code for token."""
    # Exchange code for short-lived token
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": settings.instagram_app_id,
                "client_secret": settings.instagram_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.app_base_url}/api/social/callback/instagram",
                "code": code,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to exchange code for token"
            )
        token_data = resp.json()

    access_token = token_data.get("access_token", "")
    ig_user_id = token_data.get("user_id", "")

    # Get account info
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            f"https://graph.instagram.com/v22.0/{ig_user_id}",
            params={
                "fields": "username",
                "access_token": access_token,
            },
        )
        account_name = ""
        if profile_resp.status_code == 200:
            account_name = profile_resp.json().get("username", "")

    agent = _get_user_social_agent(user, db)

    account = SocialAccount(
        user_id=user.id,
        agent_id=agent.id,
        platform="instagram",
        access_token=access_token,
        account_name=account_name or f"instagram-{ig_user_id}",
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    return OAuthCallbackResponse(
        detail="Instagram account connected", account_id=account.id
    )


@router.post("/connect/facebook", response_model=OAuthUrlResponse)
async def connect_facebook(
    agent_id: int | None = Query(default=None),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Initiate Facebook OAuth flow. Returns the authorization URL."""
    if agent_id:
        agent = db.get(Agent, agent_id)
        if not agent or agent.user_id != user.id:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        _get_user_social_agent(user, db)

    state = _generate_state(user.id)
    params = {
        "client_id": settings.facebook_app_id,
        "redirect_uri": f"{settings.app_base_url}/api/social/callback/facebook",
        "scope": "pages_show_list,pages_read_engagement,pages_manage_posts,pages_manage_metadata",
        "response_type": "code",
        "state": state,
    }
    auth_url = f"https://www.facebook.com/v22.0/dialog/oauth?{urlencode(params)}"
    return OAuthUrlResponse(auth_url=auth_url, state=state)


@router.get("/callback/facebook", response_model=OAuthCallbackResponse)
async def callback_facebook(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Handle Facebook OAuth callback. Exchange code for token."""
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.facebook.com/v22.0/oauth/access_token",
            params={
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "redirect_uri": f"{settings.app_base_url}/api/social/callback/facebook",
                "code": code,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to exchange code for token"
            )
        token_data = resp.json()

    access_token = token_data.get("access_token", "")

    # Get user profile
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            "https://graph.facebook.com/v22.0/me",
            params={
                "fields": "name",
                "access_token": access_token,
            },
        )
        account_name = ""
        if profile_resp.status_code == 200:
            account_name = profile_resp.json().get("name", "")

    agent = _get_user_social_agent(user, db)

    account = SocialAccount(
        user_id=user.id,
        agent_id=agent.id,
        platform="facebook",
        access_token=access_token,
        account_name=account_name or "facebook-user",
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    return OAuthCallbackResponse(
        detail="Facebook account connected", account_id=account.id
    )


@router.get("/accounts", response_model=list[SocialAccountResponse])
async def list_accounts(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all connected social media accounts for the current user."""
    accounts = db.exec(
        select(SocialAccount).where(SocialAccount.user_id == user.id)
    ).all()
    return accounts


@router.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Disconnect (delete) a social media account."""
    account = _get_account_or_404(account_id, user, db)
    db.delete(account)
    db.commit()
    return {"detail": "Account disconnected"}


# --- Feed & content ---


@router.get("/feed")
async def get_feed(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get posts from all connected accounts (IG + FB)."""
    accounts = db.exec(
        select(SocialAccount).where(SocialAccount.user_id == user.id)
    ).all()

    all_posts: list[dict] = []
    for account in accounts:
        try:
            if account.platform == "instagram":
                svc = InstagramService(account.access_token)
                posts = await svc.get_media()
                for post in posts:
                    post["platform"] = "instagram"
                    post["account_name"] = account.account_name
                all_posts.extend(posts)
                await svc.close()
            elif account.platform == "facebook":
                svc = FacebookService(account.access_token)
                posts = await svc.get_posts()
                for post in posts:
                    post["platform"] = "facebook"
                    post["account_name"] = account.account_name
                all_posts.extend(posts)
                await svc.close()
        except Exception:
            # Skip accounts that fail (expired token, etc.)
            continue

    return {"posts": all_posts}


@router.get("/stories")
async def get_stories(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get stories from connected Instagram accounts."""
    accounts = db.exec(
        select(SocialAccount).where(
            SocialAccount.user_id == user.id,
            SocialAccount.platform == "instagram",
        )
    ).all()

    all_stories: list[dict] = []
    for account in accounts:
        try:
            svc = InstagramService(account.access_token)
            stories = await svc.get_stories()
            for story in stories:
                story["account_name"] = account.account_name
            all_stories.extend(stories)
            await svc.close()
        except Exception:
            continue

    return {"stories": all_stories}


@router.post("/posts", response_model=PublishPostResponse)
async def publish_post(
    body: PublishPostRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Publish a post to specified platforms."""
    accounts = db.exec(
        select(SocialAccount).where(SocialAccount.user_id == user.id)
    ).all()

    accounts_by_platform = {a.platform: a for a in accounts}
    results: list[dict] = []

    for platform in body.platforms:
        account = accounts_by_platform.get(platform)
        if not account:
            results.append(
                {"platform": platform, "success": False, "error": "No account connected"}
            )
            continue

        try:
            if platform == "instagram":
                if not body.image_url:
                    results.append(
                        {
                            "platform": "instagram",
                            "success": False,
                            "error": "Instagram requires an image_url",
                        }
                    )
                    continue
                svc = InstagramService(account.access_token)
                result = await svc.publish_post(body.image_url, body.message)
                results.append(
                    {"platform": "instagram", "success": True, "data": result}
                )
                await svc.close()
            elif platform == "facebook":
                svc = FacebookService(account.access_token)
                result = await svc.publish_post(body.message, body.image_url)
                results.append(
                    {"platform": "facebook", "success": True, "data": result}
                )
                await svc.close()
            else:
                results.append(
                    {"platform": platform, "success": False, "error": "Unsupported platform"}
                )
        except Exception as e:
            results.append(
                {"platform": platform, "success": False, "error": str(e)}
            )

    return PublishPostResponse(results=results)


@router.get("/comments/{post_id}")
async def get_comments(
    post_id: str,
    platform: str = Query(..., description="instagram or facebook"),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get comments for a post."""
    account = db.exec(
        select(SocialAccount).where(
            SocialAccount.user_id == user.id,
            SocialAccount.platform == platform,
        )
    ).first()
    if not account:
        raise HTTPException(
            status_code=404, detail=f"No {platform} account connected"
        )

    try:
        if platform == "instagram":
            svc = InstagramService(account.access_token)
            comments = await svc.get_comments(post_id)
            await svc.close()
        elif platform == "facebook":
            svc = FacebookService(account.access_token)
            comments = await svc.get_comments(post_id)
            await svc.close()
        else:
            raise HTTPException(status_code=400, detail="Unsupported platform")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"API error: {e}")

    return {"comments": comments}


@router.post("/comments/{comment_id}/reply")
async def reply_to_comment(
    comment_id: str,
    body: ReplyRequest,
    platform: str = Query(..., description="instagram or facebook"),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Reply to a comment."""
    account = db.exec(
        select(SocialAccount).where(
            SocialAccount.user_id == user.id,
            SocialAccount.platform == platform,
        )
    ).first()
    if not account:
        raise HTTPException(
            status_code=404, detail=f"No {platform} account connected"
        )

    try:
        if platform == "instagram":
            svc = InstagramService(account.access_token)
            result = await svc.reply_to_comment(comment_id, body.message)
            await svc.close()
        elif platform == "facebook":
            svc = FacebookService(account.access_token)
            result = await svc.reply_to_comment(comment_id, body.message)
            await svc.close()
        else:
            raise HTTPException(status_code=400, detail="Unsupported platform")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"API error: {e}")

    return {"result": result}


@router.get("/dms")
async def get_dms(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get DMs from connected Instagram accounts."""
    account = db.exec(
        select(SocialAccount).where(
            SocialAccount.user_id == user.id,
            SocialAccount.platform == "instagram",
        )
    ).first()
    if not account:
        raise HTTPException(
            status_code=404, detail="No Instagram account connected"
        )

    try:
        svc = InstagramService(account.access_token)
        conversations = await svc.get_conversations()
        await svc.close()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"API error: {e}")

    return {"conversations": conversations}


@router.post("/dms/{thread_id}/reply")
async def reply_to_dm(
    thread_id: str,
    body: ReplyRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Reply to a DM thread."""
    account = db.exec(
        select(SocialAccount).where(
            SocialAccount.user_id == user.id,
            SocialAccount.platform == "instagram",
        )
    ).first()
    if not account:
        raise HTTPException(
            status_code=404, detail="No Instagram account connected"
        )

    try:
        svc = InstagramService(account.access_token)
        result = await svc.send_message(thread_id, body.message)
        await svc.close()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"API error: {e}")

    return {"result": result}


# --- AI assistant ---


@router.post("/ai/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    user: User = Depends(get_current_user),
):
    """AI content assistant (stub - returns placeholder)."""
    return AIChatResponse(
        reply="I'm your social media AI assistant. LLM integration coming soon."
    )
