# Meta (Instagram + Facebook) Graph API Research

**Date:** 2026-02-17
**Purpose:** Social media management tool - API capabilities, endpoints, auth, Python integration

---

## 1. Authentication (OAuth 2.0)

### Two Authentication Paths

**Option A: Instagram Login (Instagram Direct Login)**
- Direct OAuth via Instagram, generates Instagram User access tokens
- Best for single-account, user-facing apps
- Uses `api.instagram.com` endpoints
- Scopes: `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_messages`, etc.

**Option B: Facebook Login for Business**
- OAuth through Facebook, accesses Instagram via connected Facebook Pages
- Best for multi-account, enterprise tools
- Uses `graph.facebook.com` endpoints
- Scopes: `pages_show_list`, `pages_manage_posts`, `instagram_basic`, `instagram_manage_insights`, etc.

### OAuth Flow (Instagram Direct Login)

```python
import httpx
import secrets

# Step 1: Generate authorization URL
APP_ID = "your_app_id"
APP_SECRET = "your_app_secret"
REDIRECT_URI = "https://yourapp.com/callback"
API_VERSION = "v22.0"

state = secrets.token_urlsafe(32)
auth_url = (
    f"https://www.instagram.com/oauth/authorize"
    f"?client_id={APP_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope=instagram_business_basic,instagram_business_content_publish,instagram_business_manage_messages,instagram_business_manage_comments"
    f"&response_type=code"
    f"&state={state}"
)
# Redirect user to auth_url

# Step 2: Exchange authorization code for short-lived token
async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code": code,
            },
        )
        return response.json()  # {"access_token": "...", "user_id": "..."}

# Step 3: Exchange short-lived token for long-lived token (60 days)
async def get_long_lived_token(short_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.instagram.com/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": APP_SECRET,
                "access_token": short_token,
            },
        )
        return response.json()  # {"access_token": "...", "token_type": "bearer", "expires_in": 5184000}

# Step 4: Refresh long-lived token before expiry
async def refresh_long_lived_token(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.instagram.com/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": token,
            },
        )
        return response.json()
```

### OAuth Flow (Facebook Login - for Facebook Pages + connected Instagram)

```python
# Step 1: Authorization URL
auth_url = (
    f"https://www.facebook.com/{API_VERSION}/dialog/oauth"
    f"?client_id={APP_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope=pages_show_list,pages_read_engagement,pages_manage_posts,pages_manage_metadata,"
    f"instagram_basic,instagram_manage_insights,instagram_content_publish,"
    f"instagram_manage_comments,instagram_manage_messages"
    f"&response_type=code"
    f"&state={state}"
)

# Step 2: Exchange code for user access token
async def exchange_code_fb(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://graph.facebook.com/{API_VERSION}/oauth/access_token",
            params={
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": code,
            },
        )
        return response.json()  # {"access_token": "...", "token_type": "bearer", "expires_in": ...}

# Step 3: Exchange for long-lived user token (60 days)
async def get_long_lived_token_fb(short_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://graph.facebook.com/{API_VERSION}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "fb_exchange_token": short_token,
            },
        )
        return response.json()

# Step 4: Get Page Access Token (never expires if derived from long-lived user token)
async def get_page_access_token(user_token: str, page_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://graph.facebook.com/{API_VERSION}/{page_id}",
            params={
                "fields": "access_token",
                "access_token": user_token,
            },
        )
        return response.json()["access_token"]

# Step 5: Get Instagram Business Account ID connected to Page
async def get_ig_account_id(page_token: str, page_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://graph.facebook.com/{API_VERSION}/{page_id}",
            params={
                "fields": "instagram_business_account",
                "access_token": page_token,
            },
        )
        return response.json()["instagram_business_account"]["id"]
```

### Token Lifecycle

| Token Type | Duration | Refresh |
|---|---|---|
| Short-lived user token | ~1 hour | Exchange code again |
| Long-lived user token | 60 days | Refresh before expiry |
| Page access token (from long-lived user) | Never expires | N/A |
| Instagram user token (direct login) | 60 days | Refresh endpoint |

---

## 2. Reading Posts with Metrics

### Get User's Media (Instagram)

```python
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

async def get_ig_posts(ig_user_id: str, access_token: str, limit: int = 25) -> dict:
    """Get user's Instagram posts with basic metrics."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{ig_user_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
                "limit": limit,
                "access_token": access_token,
            },
        )
        return response.json()
    # Returns: {"data": [{"id": "...", "caption": "...", "like_count": 42, ...}], "paging": {...}}

async def get_ig_post_insights(media_id: str, access_token: str) -> dict:
    """Get detailed insights for a specific post."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{media_id}/insights",
            params={
                "metric": "impressions,reach,saved,shares,total_interactions",
                "access_token": access_token,
            },
        )
        return response.json()
    # Returns: {"data": [{"name": "impressions", "values": [{"value": 1234}]}, ...]}

async def get_ig_account_insights(ig_user_id: str, access_token: str) -> dict:
    """Get account-level insights (reach, impressions, follower count)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{ig_user_id}/insights",
            params={
                "metric": "impressions,reach,accounts_engaged,follows_and_unfollows",
                "period": "day",
                "access_token": access_token,
            },
        )
        return response.json()
```

### Get Facebook Page Posts

```python
async def get_fb_page_posts(page_id: str, page_token: str, limit: int = 25) -> dict:
    """Get Facebook Page posts with metrics."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{page_id}/posts",
            params={
                "fields": "id,message,created_time,full_picture,permalink_url,"
                          "likes.summary(true),comments.summary(true),shares",
                "limit": limit,
                "access_token": page_token,
            },
        )
        return response.json()

async def get_fb_post_insights(post_id: str, page_token: str) -> dict:
    """Get detailed insights for a Facebook post."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{post_id}/insights",
            params={
                "metric": "post_impressions,post_reach,post_engaged_users,post_clicks",
                "access_token": page_token,
            },
        )
        return response.json()
```

### Available Media Metrics (Instagram, as of v22.0+)

| Metric | Media Types | Description |
|---|---|---|
| `impressions` | IMAGE, VIDEO, CAROUSEL | Total times seen |
| `reach` | IMAGE, VIDEO, CAROUSEL | Unique accounts reached |
| `saved` | IMAGE, VIDEO, CAROUSEL | Times saved |
| `shares` | IMAGE, VIDEO, CAROUSEL | Times shared |
| `total_interactions` | All | Total interactions |
| `likes` | IMAGE, VIDEO, CAROUSEL | Like count |
| `comments` | IMAGE, VIDEO, CAROUSEL | Comment count |
| `plays` | VIDEO, REEL | Video plays |
| `ig_reels_avg_watch_time` | REEL | Average watch time |
| `ig_reels_video_view_total_time` | REEL | Total view time |

**Deprecated (v21+):** `video_views` (non-Reels), `email_contacts`, `profile_views`, `website_clicks`, `phone_call_clicks`, `text_message_clicks`

---

## 3. Reading Stories

```python
async def get_ig_stories(ig_user_id: str, access_token: str) -> dict:
    """Get currently active stories (available for 24h only)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{ig_user_id}/stories",
            params={
                "fields": "id,media_type,media_url,timestamp,caption",
                "access_token": access_token,
            },
        )
        return response.json()
    # Returns only stories still live (within 24h window)

async def get_ig_story_insights(story_media_id: str, access_token: str) -> dict:
    """Get insights for a specific story. Must be queried while story is live or within 24h of expiry."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{story_media_id}/insights",
            params={
                "metric": "impressions,reach,replies,exits,taps_forward,taps_back",
                "access_token": access_token,
            },
        )
        return response.json()
```

### Story Insights Metrics

| Metric | Description |
|---|---|
| `impressions` | Total views |
| `reach` | Unique accounts reached |
| `replies` | Number of replies |
| `exits` | Times users swiped away |
| `taps_forward` | Taps to next story |
| `taps_back` | Taps to previous story |

**Important:** Stories data is only available while the story is live (24 hours) and briefly after expiry. Story insights must be collected proactively.

---

## 4. Publishing Posts

### Instagram: Image Post (Two-Step Container Flow)

```python
async def publish_ig_image(
    ig_user_id: str,
    image_url: str,
    caption: str,
    access_token: str,
) -> dict:
    """Publish an image post to Instagram. Image must be publicly accessible URL, JPEG format."""
    async with httpx.AsyncClient() as client:
        # Step 1: Create media container
        container_resp = await client.post(
            f"{BASE_URL}/{ig_user_id}/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": access_token,
            },
        )
        container_id = container_resp.json()["id"]

        # Step 2: Wait for container to be ready (poll status)
        import asyncio
        for _ in range(30):
            status_resp = await client.get(
                f"{BASE_URL}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": access_token,
                },
            )
            status = status_resp.json().get("status_code")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                raise Exception(f"Container processing failed: {status_resp.json()}")
            await asyncio.sleep(2)

        # Step 3: Publish the container
        publish_resp = await client.post(
            f"{BASE_URL}/{ig_user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": access_token,
            },
        )
        return publish_resp.json()  # {"id": "published_media_id"}
```

### Instagram: Carousel Post

```python
async def publish_ig_carousel(
    ig_user_id: str,
    image_urls: list[str],
    caption: str,
    access_token: str,
) -> dict:
    """Publish a carousel post (2-10 images)."""
    async with httpx.AsyncClient() as client:
        # Step 1: Create individual item containers
        item_ids = []
        for url in image_urls:
            resp = await client.post(
                f"{BASE_URL}/{ig_user_id}/media",
                params={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": access_token,
                },
            )
            item_ids.append(resp.json()["id"])

        # Step 2: Create carousel container
        carousel_resp = await client.post(
            f"{BASE_URL}/{ig_user_id}/media",
            params={
                "media_type": "CAROUSEL",
                "children": ",".join(item_ids),
                "caption": caption,
                "access_token": access_token,
            },
        )
        carousel_id = carousel_resp.json()["id"]

        # Step 3: Publish
        publish_resp = await client.post(
            f"{BASE_URL}/{ig_user_id}/media_publish",
            params={
                "creation_id": carousel_id,
                "access_token": access_token,
            },
        )
        return publish_resp.json()
```

### Instagram: Story Post

```python
async def publish_ig_story(
    ig_user_id: str,
    image_url: str,
    access_token: str,
) -> dict:
    """Publish an image story to Instagram."""
    async with httpx.AsyncClient() as client:
        # Step 1: Create story container
        container_resp = await client.post(
            f"{BASE_URL}/{ig_user_id}/media",
            params={
                "image_url": image_url,
                "media_type": "STORIES",
                "access_token": access_token,
            },
        )
        container_id = container_resp.json()["id"]

        # Step 2: Publish
        publish_resp = await client.post(
            f"{BASE_URL}/{ig_user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": access_token,
            },
        )
        return publish_resp.json()
```

### Facebook Page: Text + Image Post

```python
async def publish_fb_photo_post(
    page_id: str,
    page_token: str,
    message: str,
    image_url: str | None = None,
    image_path: str | None = None,
) -> dict:
    """Publish a photo post to a Facebook Page."""
    async with httpx.AsyncClient() as client:
        if image_url:
            # Option A: Image from URL
            response = await client.post(
                f"{BASE_URL}/{page_id}/photos",
                params={
                    "url": image_url,
                    "message": message,
                    "access_token": page_token,
                },
            )
        elif image_path:
            # Option B: Upload local file
            with open(image_path, "rb") as f:
                response = await client.post(
                    f"{BASE_URL}/{page_id}/photos",
                    data={
                        "message": message,
                        "access_token": page_token,
                    },
                    files={"source": f},
                )
        return response.json()  # {"id": "photo_id", "post_id": "page_post_id"}

async def publish_fb_text_post(page_id: str, page_token: str, message: str) -> dict:
    """Publish a text-only post to a Facebook Page."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{page_id}/feed",
            params={
                "message": message,
                "access_token": page_token,
            },
        )
        return response.json()
```

### Publishing Constraints

- Instagram images must be publicly accessible URLs (no local file upload)
- Instagram supports JPEG only
- Max caption: 2,200 characters
- Max 30 hashtags per post
- Max 30 mentions per post
- **Publishing rate limit: 25 posts per 24-hour rolling window per IG account**
- Facebook supports both URL and local file upload

---

## 5. Comments - Read and Reply

### Instagram Comments

```python
async def get_ig_comments(media_id: str, access_token: str) -> dict:
    """Get comments on a specific Instagram post."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{media_id}/comments",
            params={
                "fields": "id,text,username,timestamp,like_count,replies{id,text,username,timestamp}",
                "access_token": access_token,
            },
        )
        return response.json()

async def reply_to_ig_comment(comment_id: str, message: str, access_token: str) -> dict:
    """Reply to a specific Instagram comment."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{comment_id}/replies",
            params={
                "message": message,
                "access_token": access_token,
            },
        )
        return response.json()  # {"id": "new_comment_id"}

async def hide_ig_comment(comment_id: str, access_token: str) -> dict:
    """Hide a comment on Instagram."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{comment_id}",
            params={
                "hide": "true",
                "access_token": access_token,
            },
        )
        return response.json()

async def delete_ig_comment(comment_id: str, access_token: str) -> dict:
    """Delete your own comment on Instagram."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{BASE_URL}/{comment_id}",
            params={"access_token": access_token},
        )
        return response.json()
```

### Facebook Page Comments

```python
async def get_fb_comments(post_id: str, page_token: str) -> dict:
    """Get comments on a Facebook Page post."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{post_id}/comments",
            params={
                "fields": "id,message,from,created_time,like_count,comment_count",
                "access_token": page_token,
            },
        )
        return response.json()

async def reply_to_fb_comment(comment_id: str, message: str, page_token: str) -> dict:
    """Reply to a Facebook comment."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{comment_id}/comments",
            params={
                "message": message,
                "access_token": page_token,
            },
        )
        return response.json()
```

---

## 6. Direct Messages (DMs)

### Important Prerequisites
- Uses the **Messenger Platform API** (not the standard Graph API)
- Only Business/Creator accounts
- Requires `instagram_manage_messages` (FB Login) or `instagram_business_manage_messages` (IG Login)
- User must initiate the conversation first (business cannot cold-message)
- 24-hour messaging window after last user message
- Requires webhook setup for real-time message reception
- Requires App Review for production access

### Webhook Setup (Flask Example)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import httpx

app = Flask(__name__)
VERIFY_TOKEN = "your_verify_token"
PAGE_ACCESS_TOKEN = "your_page_access_token"
APP_SECRET = "your_app_secret"

# Webhook verification (GET) - Meta sends this to verify your endpoint
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

# Webhook handler (POST) - receives incoming messages
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    payload = request.get_data()
    expected = "sha256=" + hmac.new(
        APP_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return "Invalid signature", 403

    data = request.get_json()

    for entry in data.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            sender_id = messaging_event["sender"]["id"]
            if "message" in messaging_event:
                message_text = messaging_event["message"].get("text", "")
                print(f"Received from {sender_id}: {message_text}")
                # Process and reply
                send_message(sender_id, f"Thanks for your message!")

    return "OK", 200

def send_message(recipient_id: str, message_text: str):
    """Send a reply message via Instagram Messaging API."""
    url = f"https://graph.facebook.com/{API_VERSION}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE",
        "access_token": PAGE_ACCESS_TOKEN,
    }
    response = httpx.post(url, json=payload)
    return response.json()

def send_image_message(recipient_id: str, image_url: str):
    """Send an image via Instagram DM."""
    url = f"https://graph.facebook.com/{API_VERSION}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url},
            }
        },
        "messaging_type": "RESPONSE",
        "access_token": PAGE_ACCESS_TOKEN,
    }
    response = httpx.post(url, json=payload)
    return response.json()
```

### Reading Conversation History

```python
async def get_ig_conversations(page_id: str, page_token: str) -> dict:
    """Get list of Instagram DM conversations."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{page_id}/conversations",
            params={
                "platform": "instagram",
                "fields": "participants,updated_time,messages{message,from,created_time}",
                "access_token": page_token,
            },
        )
        return response.json()

async def get_conversation_messages(conversation_id: str, page_token: str) -> dict:
    """Get messages within a specific conversation."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{conversation_id}/messages",
            params={
                "fields": "id,message,from,created_time,attachments",
                "access_token": page_token,
            },
        )
        return response.json()
```

### Facebook Page DMs (same Messenger API pattern)

```python
async def get_fb_conversations(page_id: str, page_token: str) -> dict:
    """Get Facebook Messenger conversations for a Page."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{page_id}/conversations",
            params={
                "fields": "participants,updated_time,messages{message,from,created_time}",
                "access_token": page_token,
            },
        )
        return response.json()

# Sending FB messages uses the same /me/messages endpoint as Instagram
```

### DM Constraints

- Business cannot initiate conversations; user must message first
- 24-hour window: can reply within 24h of last user message
- After 24h: can only send "message tags" (limited categories)
- Max text message: 1,000 bytes (UTF-8)
- Max image attachment: 8 MB (PNG, JPEG, GIF)
- Max video attachment: 25 MB (MP4, MOV)
- Webhook must respond with 200 within 30 seconds
- 5 retry attempts on webhook failure

---

## 7. Required Permissions / Scopes

### For Facebook Login (managing Pages + connected Instagram)

| Permission | Purpose |
|---|---|
| `pages_show_list` | List user's Facebook Pages |
| `pages_read_engagement` | Read Page engagement data |
| `pages_manage_posts` | Create/edit/delete Page posts |
| `pages_manage_metadata` | Subscribe to webhooks |
| `pages_manage_engagement` | Manage comments on Page |
| `pages_messaging` | Send/receive Messenger messages on Page |
| `instagram_basic` | Read Instagram profile and media |
| `instagram_manage_insights` | Read Instagram insights/analytics |
| `instagram_content_publish` | Publish content to Instagram |
| `instagram_manage_comments` | Read/reply/delete Instagram comments |
| `instagram_manage_messages` | Send/receive Instagram DMs |
| `business_management` | Access business assets (optional, for Business Manager) |

### For Instagram Login (direct Instagram API)

| Permission | Purpose |
|---|---|
| `instagram_business_basic` | Read profile info, media |
| `instagram_business_content_publish` | Publish posts, stories, reels |
| `instagram_business_manage_messages` | DM access |
| `instagram_business_manage_comments` | Comment management |

### App Review
- All permissions except `pages_show_list` and basic profile require **App Review** by Meta
- Review can take days to weeks
- Must provide detailed use-case justification and screencast demo
- Development mode: only test users can use the app

---

## 8. Rate Limits

### Instagram Graph API

| Limit Type | Value | Details |
|---|---|---|
| API calls | **200 requests/hour per IG account** | Rolling window. Was 4,800/hr before 2025 reduction |
| Content publishing | **25 posts per 24h** per account | Enforced at `media_publish` endpoint |
| DM sending | **200 messages/hour** per account | Separate from API call limit |
| DM per user | **1 automated message/24h** per user | Comment/story-trigger automation only |

### Facebook Graph API

| Limit Type | Value | Details |
|---|---|---|
| App-level | ~200 calls/user/hour | Based on total app users |
| Page-level | Varies by endpoint | Monitor `X-Page-Usage` header |
| Business Use Case | Custom | Monitor `X-Business-Use-Case-Usage` header |

### Rate Limit Headers

```python
# Check rate limit status from response headers
def check_rate_limits(response: httpx.Response):
    app_usage = response.headers.get("X-App-Usage")  # JSON: {"call_count": %, "total_cputime": %, "total_time": %}
    page_usage = response.headers.get("X-Page-Usage")  # same format
    business_usage = response.headers.get("X-Business-Use-Case-Usage")
    return {
        "app_usage": app_usage,
        "page_usage": page_usage,
        "business_usage": business_usage,
    }
```

### Rate Limit Best Practices
- Implement exponential backoff on HTTP 429
- Cache responses (static content 24h, metrics 1-6h)
- Use field selection to reduce payload size
- Use webhooks instead of polling where possible
- Batch requests where supported
- Monitor `X-App-Usage` and `X-Page-Usage` headers proactively

---

## 9. Python Libraries

### Option 1: `httpx` / `requests` (Direct API Calls) -- RECOMMENDED

Best for full control and understanding of the API. All examples in this document use this approach.

```bash
pip install httpx
```

Pros: Full control, no abstraction overhead, works with latest API versions immediately
Cons: More boilerplate code

### Option 2: `facebook-business` (Official Meta SDK)

```bash
pip install facebook-business
```

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.page import Page
from facebook_business.adobjects.iguser import IGUser

# Initialize
FacebookAdsApi.init(app_id=APP_ID, app_secret=APP_SECRET, access_token=ACCESS_TOKEN)

# Get IG user media
ig_user = IGUser(ig_user_id)
media = ig_user.get_media(fields=["id", "caption", "like_count", "comments_count", "timestamp"])

# Get Page posts
page = Page(page_id)
posts = page.get_posts(fields=["id", "message", "created_time"])
```

Pros: Official, type-safe objects, supports Marketing API
Cons: Heavy (marketing-focused), can lag behind API version updates, large dependency

### Option 3: `python-facebook-api` (Third-party Wrapper)

```bash
pip install python-facebook-api
```

```python
from pyfacebook import GraphAPI

# Initialize with token
api = GraphAPI(access_token="your_token", version="v22.0")

# Get object
result = api.get_object(object_id=ig_user_id, fields="id,username,media_count")

# Get connections
media = api.get_connection(object_id=ig_user_id, connection="media",
                           fields="id,caption,like_count,timestamp")
```

Pros: Lightweight, Pythonic, supports both FB and IG
Cons: Third-party maintained, may lag on updates

### Option 4: `facebook-sdk` (Legacy)

```bash
pip install facebook-sdk
```

```python
import facebook

graph = facebook.GraphAPI(access_token="your_token", version="3.1")
posts = graph.get_connections(id="me", connection_name="posts")
```

Pros: Simple, widely known
Cons: Outdated, not actively maintained, old API version default

### Library Comparison

| Library | PyPI | Maintained | IG Support | FB Support | Best For |
|---|---|---|---|---|---|
| `httpx`/`requests` | Yes | Yes | Full | Full | Custom integration, latest API |
| `facebook-business` | Yes | Meta official | Yes | Yes | Ads/Marketing heavy use |
| `python-facebook-api` | Yes | Community | Yes | Yes | Quick prototyping |
| `facebook-sdk` | Yes | Barely | Limited | Yes | Legacy projects only |

**Recommendation:** Use `httpx` directly for maximum control and immediate compatibility with API changes. Wrap in your own service classes.

---

## 10. API Version & Deprecation Notes

- **Current stable:** v22.0 (April 2025)
- **Latest:** v23.0 (May 2025), v24.0 expected 2026
- **Minimum supported:** v22.0+ (as of September 2025, older versions rejected)
- **Base URL:** `https://graph.facebook.com/v22.0/`
- **Instagram direct login base:** `https://graph.instagram.com/`

### Key Deprecations (2024-2025)
- Basic Display API: **Dead** (December 4, 2024). Personal accounts no longer accessible.
- `video_views` metric (non-Reels): Deprecated in v21+
- `email_contacts`, `profile_views`, `website_clicks`, `phone_call_clicks`, `text_message_clicks`: Deprecated in v21+
- Old Instagram User/Media/Comment endpoints replaced by IG User/IG Media/IG Comment in v22+

---

## 11. Architecture Recommendation for Social Media Manager

```
┌─────────────────────────────────────────────┐
│              Social Media Manager           │
├─────────────────────────────────────────────┤
│  Auth Service                               │
│  ├── OAuth flow (FB Login + IG Login)       │
│  ├── Token storage (encrypted in DB)        │
│  └── Token refresh scheduler (cron)         │
├─────────────────────────────────────────────┤
│  Meta API Client (httpx-based)              │
│  ├── Rate limiter (200 req/hr/account)      │
│  ├── Retry with exponential backoff         │
│  ├── Response caching                       │
│  └── Pagination handler                     │
├─────────────────────────────────────────────┤
│  Content Service                            │
│  ├── Post publisher (IG container flow)     │
│  ├── Story publisher                        │
│  ├── FB Page publisher                      │
│  └── Media upload/hosting                   │
├─────────────────────────────────────────────┤
│  Analytics Service                          │
│  ├── Post metrics collector                 │
│  ├── Story metrics collector (24h window!)  │
│  ├── Account insights aggregator            │
│  └── Scheduled data fetcher                 │
├─────────────────────────────────────────────┤
│  Engagement Service                         │
│  ├── Comment reader/replier                 │
│  ├── DM webhook handler (Flask/FastAPI)     │
│  ├── DM conversation reader                 │
│  └── Auto-reply rules engine                │
├─────────────────────────────────────────────┤
│  Webhook Server (FastAPI)                   │
│  ├── /webhook GET (verification)            │
│  ├── /webhook POST (message handler)        │
│  └── Signature validation                   │
└─────────────────────────────────────────────┘
```

### Key Implementation Considerations

1. **Token refresh**: Set up a cron/scheduler to refresh tokens before 60-day expiry
2. **Story insights**: Must poll within 24h of story going live; schedule collection
3. **Image hosting**: Instagram requires publicly accessible URLs; use S3/CloudFlare R2
4. **Rate limiting**: Implement token bucket or sliding window per account
5. **Webhook security**: Always validate `X-Hub-Signature-256` header
6. **App Review**: Start early; prepare detailed use-case docs and video demo
7. **Error handling**: Handle `OAuthException` (token expired), `GraphMethodException` (permission denied), HTTP 429 (rate limit)
