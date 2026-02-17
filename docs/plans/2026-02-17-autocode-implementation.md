# AutoCode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a PWA web application for managing multiple independent AI agents — coding (nanobot → Claude Code), research (chat over Claude Code), learning (AI tutor), and social media (IG/FB management with AI assistant).

**Architecture:** FastAPI backend with SQLite (SQLModel), React 19 PWA frontend with TypeScript/Vite/Tailwind. Agents run as isolated subprocesses. Coding agent uses nanobot-ai to manage Claude Code via tmux. Research agent wraps Claude Code chat sessions. Learning agent uses nanobot-ai directly. Social media agent integrates Instagram/Facebook Graph APIs.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite, React 19, TypeScript, Vite, Tailwind CSS, vite-plugin-pwa, xterm.js, nanobot-ai, tmux

**Design doc:** `docs/plans/2026-02-17-autocode-design.md`

---

## Phase 1: Backend Foundation

### Task 1: Initialize Backend Project

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

**Step 1: Create backend directory and pyproject.toml**

```toml
[project]
name = "autocode"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlmodel>=0.0.22",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "python-multipart>=0.0.18",
    "nanobot-ai>=0.1.3",
    "httpx>=0.28",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.24", "httpx>=0.28"]
```

**Step 2: Create app/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///autocode.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    data_dir: str = "/data/users"
    encryption_key: str = "change-me-in-production"

    class Config:
        env_prefix = "AUTOCODE_"

settings = Settings()
```

**Step 3: Create app/main.py with FastAPI skeleton**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AutoCode", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Install dependencies and verify server starts**

Run: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`
Expected: Server running on http://127.0.0.1:8000, /health returns {"status": "ok"}

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: initialize FastAPI backend skeleton"
```

---

### Task 2: Database Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/agent.py`
- Create: `backend/app/models/project.py`
- Create: `backend/app/models/research.py`
- Create: `backend/app/models/learning.py`
- Create: `backend/app/models/social.py`
- Create: `backend/app/models/common.py`
- Create: `backend/app/database.py`

**Step 1: Create database.py with engine and session**

```python
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

engine = create_engine(settings.database_url, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
```

**Step 2: Create user model**

```python
from sqlmodel import SQLModel, Field
from datetime import datetime

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="user")  # "admin" | "user"
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 3: Create agent model**

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import json

class Agent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    type: str  # "coding" | "research" | "learning" | "social_media" | "custom"
    model: str = Field(default="anthropic/claude-opus-4-6")
    identity: str = Field(default="")
    tools: str = Field(default="[]")  # JSON array
    mcp_servers: str = Field(default="[]")  # JSON array
    global_rules: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 4: Create project model (coding agent)**

```python
class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    name: str
    slug: str
    description: str = Field(default="")
    architecture: str = Field(default="")
    implementation_plan: str = Field(default="[]")  # JSON
    status: str = Field(default="created")
    current_step: int = Field(default=0)
    tmux_session: str = Field(default="")
    workspace_path: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 5: Create research session model**

```python
class ResearchSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    name: str
    slug: str
    status: str = Field(default="active")
    tmux_session: str = Field(default="")
    workspace_path: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 6: Create learning models (subject + course)**

```python
class LearningSubject(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LearningCourse(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    subject_id: int = Field(foreign_key="learningsubject.id", index=True)
    name: str
    instructions: str = Field(default="")
    chat_history_path: str = Field(default="")
    student_notes_path: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 7: Create social media models**

```python
class SocialAccount(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    platform: str  # "instagram" | "facebook"
    access_token: str  # encrypted
    account_name: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 8: Create common models (chat messages, agent instances, logs, API keys)**

```python
class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    session_type: str  # "research" | "learning" | "social_ai"
    session_id: int
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentInstance(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    project_id: int | None = Field(default=None, foreign_key="project.id")
    pid: int | None = Field(default=None)
    status: str = Field(default="stopped")
    started_at: datetime | None = Field(default=None)
    stopped_at: datetime | None = Field(default=None)

class Log(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key="project.id")
    agent_instance_id: int | None = Field(default=None, foreign_key="agentinstance.id")
    level: str = Field(default="info")
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ApiKey(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str
    encrypted_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 9: Create __init__.py that imports all models, wire up init_db in main.py**

**Step 10: Run app, verify tables are created**

Run: `cd backend && python -c "from app.database import init_db; init_db()"`
Expected: autocode.db created with all tables

**Step 11: Commit**

```bash
git add backend/
git commit -m "feat: add SQLModel database models"
```

---

### Task 3: Authentication System

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/deps.py`
- Test: `backend/tests/test_auth.py`

**Step 1: Write failing test for auth endpoints**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    # First create admin user via startup
    response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password():
    response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401

def test_protected_endpoint_without_token():
    response = client.get("/agents")
    assert response.status_code == 401

def test_protected_endpoint_with_token():
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    token = login.json()["access_token"]
    response = client.get("/agents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: FAIL

**Step 3: Implement auth.py (JWT creation/verification, password hashing)**

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "role": role, "exp": expire},
        settings.secret_key, algorithm="HS256"
    )

def create_refresh_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh"},
        settings.secret_key, algorithm="HS256"
    )

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
```

**Step 4: Implement api/deps.py (get_current_user dependency)**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from app.database import get_session
from app.auth import decode_token
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user
```

**Step 5: Implement api/auth.py (login + refresh endpoints)**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from app.database import get_session
from app.models.user import User
from app.auth import verify_password, create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == body.username)).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user.id, user.username, user.role),
        refresh_token=create_refresh_token(user.id),
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: dict, session: Session = Depends(get_session)):
    try:
        payload = decode_token(body["refresh_token"])
        if payload.get("type") != "refresh":
            raise ValueError
        user = session.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return TokenResponse(
        access_token=create_access_token(user.id, user.username, user.role),
        refresh_token=create_refresh_token(user.id),
    )
```

**Step 6: Wire up router in main.py, add startup event to create admin user**

Add to main.py:
```python
from contextlib import asynccontextmanager
from app.database import init_db, get_session
from app.models.user import User
from app.auth import hash_password
from sqlmodel import Session, select

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Create admin if not exists
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            session.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
            session.commit()
    yield

app = FastAPI(title="AutoCode", version="0.1.0", lifespan=lifespan)
```

**Step 7: Run tests, verify they pass**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: All PASS

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: add JWT authentication system"
```

---

### Task 4: User Management API (Admin)

**Files:**
- Create: `backend/app/api/users.py`
- Test: `backend/tests/test_users.py`

**Step 1: Write failing tests**

```python
def test_create_user(admin_client):
    response = admin_client.post("/users", json={"username": "testuser", "password": "pass123"})
    assert response.status_code == 201
    assert response.json()["username"] == "testuser"

def test_list_users(admin_client):
    response = admin_client.get("/users")
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_delete_user(admin_client):
    admin_client.post("/users", json={"username": "todelete", "password": "pass"})
    users = admin_client.get("/users").json()
    uid = [u for u in users if u["username"] == "todelete"][0]["id"]
    response = admin_client.delete(f"/users/{uid}")
    assert response.status_code == 200

def test_non_admin_cannot_manage_users(user_client):
    response = user_client.get("/users")
    assert response.status_code == 403
```

**Step 2: Run tests to verify failure**

**Step 3: Implement api/users.py**

- `GET /users` — list all users (admin only)
- `POST /users` — create user + workspace dirs (admin only)
- `DELETE /users/{id}` — delete user + cleanup workspace (admin only)

On user creation, backend creates:
```
/data/users/{username}/
├── projects/
├── research/
├── learning/
├── config/
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat: add admin user management API"
```

---

### Task 5: Agent CRUD API

**Files:**
- Create: `backend/app/api/agents.py`
- Create: `backend/app/services/agent_templates.py`
- Test: `backend/tests/test_agents.py`

**Step 1: Write failing tests**

```python
def test_create_agent_from_template(auth_client):
    response = auth_client.post("/agents", json={
        "template": "coding",
        "name": "My Coding Agent",
    })
    assert response.status_code == 201
    assert response.json()["type"] == "coding"

def test_create_custom_agent(auth_client):
    response = auth_client.post("/agents", json={
        "name": "Custom Bot",
        "type": "custom",
        "model": "anthropic/claude-sonnet-4-5",
        "identity": "You are a helpful bot.",
    })
    assert response.status_code == 201

def test_list_agents(auth_client):
    response = auth_client.get("/agents")
    assert response.status_code == 200

def test_update_agent(auth_client):
    agents = auth_client.get("/agents").json()
    aid = agents[0]["id"]
    response = auth_client.put(f"/agents/{aid}", json={"name": "Renamed Agent"})
    assert response.status_code == 200

def test_delete_agent(auth_client):
    agents = auth_client.get("/agents").json()
    aid = agents[-1]["id"]
    response = auth_client.delete(f"/agents/{aid}")
    assert response.status_code == 200
```

**Step 2: Implement agent_templates.py with pre-built templates**

```python
TEMPLATES = {
    "coding": {
        "type": "coding",
        "model": "openai/gpt-5.3-codex",
        "identity": """You are a coding agent. Your job is to manage Claude Code via tmux
and implement projects autonomously. Always:
- Break work into small steps
- Verify results after each step
- Try 3 different approaches before escalating
- Use conventional commits""",
        "tools": '["tmux", "exec", "read_file", "write_file", "web_search"]',
        "global_rules": """- Conventional commits (feat:, fix:, chore:, docs:, refactor:)
- Write tests for business logic
- Never commit secrets
- Atomic commits
- Code review before merge to main""",
    },
    "research": {
        "type": "research",
        "model": "anthropic/claude-opus-4-6",
        "identity": """You are a research agent. Search the web, analyze information,
and provide structured reports with source citations. Be thorough and verify claims
from multiple sources.""",
        "tools": '[]',  # Claude Code built-in tools
        "global_rules": "",
    },
    "learning": {
        "type": "learning",
        "model": "anthropic/claude-opus-4-6",
        "identity": """You are a personalized tutor. Adapt to the student's level,
track their progress, correct mistakes gently with explanations. Be patient and
encouraging. Always update student_notes.md after each session.""",
        "tools": '["web_search", "web_fetch", "read_file", "write_file"]',
        "global_rules": "",
    },
    "social_media": {
        "type": "social_media",
        "model": "anthropic/claude-sonnet-4-5",
        "identity": """You are a social media content assistant. Help create engaging
posts, suggest hashtags, write captions. Maintain the user's brand voice.
Be creative but professional.""",
        "tools": '[]',
        "global_rules": "",
    },
}
```

**Step 3: Implement api/agents.py**

- `GET /agents` — list user's agents (filtered by user_id)
- `POST /agents` — create from template or custom
- `GET /agents/{id}` — agent detail (verify ownership)
- `PUT /agents/{id}` — update agent config
- `DELETE /agents/{id}` — delete agent + all related data

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat: add agent CRUD with pre-built templates"
```

---

### Task 6: Tmux Manager Service

**Files:**
- Create: `backend/app/services/tmux.py`
- Test: `backend/tests/test_tmux.py`

**Step 1: Write failing tests**

```python
def test_create_session():
    manager = TmuxManager()
    manager.create_session("test-session", "/tmp")
    assert manager.session_exists("test-session")
    manager.kill_session("test-session")

def test_send_keys_and_capture():
    manager = TmuxManager()
    manager.create_session("test-capture", "/tmp")
    manager.send_keys("test-capture", "echo hello-autocode")
    import time; time.sleep(0.5)
    output = manager.capture_pane("test-capture")
    assert "hello-autocode" in output
    manager.kill_session("test-capture")

def test_kill_session():
    manager = TmuxManager()
    manager.create_session("test-kill", "/tmp")
    manager.kill_session("test-kill")
    assert not manager.session_exists("test-kill")
```

**Step 2: Run tests to verify failure**

**Step 3: Implement TmuxManager**

```python
import subprocess

class TmuxManager:
    def create_session(self, name: str, working_dir: str) -> None:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", name, "-c", working_dir],
            check=True,
        )

    def kill_session(self, name: str) -> None:
        subprocess.run(["tmux", "kill-session", "-t", name], check=False)

    def session_exists(self, name: str) -> bool:
        result = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True,
        )
        return result.returncode == 0

    def send_keys(self, name: str, keys: str) -> None:
        subprocess.run(
            ["tmux", "send-keys", "-t", name, keys, "Enter"],
            check=True,
        )

    def capture_pane(self, name: str, lines: int = 200) -> str:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", name, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True,
        )
        return result.stdout

    def list_sessions(self) -> list[str]:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True, text=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat: add tmux session manager service"
```

---

## Phase 2: Frontend Foundation

### Task 7: Initialize React Frontend

**Files:**
- Create: `frontend/` (via Vite scaffold)
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/tailwind.config.js`
- Create: `frontend/src/api/client.ts`

**Step 1: Scaffold Vite React TypeScript project**

```bash
cd /home/tomas/projects/autocode
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install axios react-router-dom @tanstack/react-query
npm install xterm @xterm/addon-fit @xterm/addon-web-links
```

**Step 2: Configure Tailwind in vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

**Step 3: Create API client with JWT interceptor**

```typescript
// src/api/client.ts
import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      // Try refresh token
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const res = await axios.post('/api/auth/refresh', { refresh_token: refresh });
          localStorage.setItem('access_token', res.data.access_token);
          localStorage.setItem('refresh_token', res.data.refresh_token);
          error.config.headers.Authorization = `Bearer ${res.data.access_token}`;
          return axios(error.config);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

**Step 4: Verify dev server runs**

Run: `cd frontend && npm run dev`
Expected: Vite dev server running on http://localhost:5173

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: initialize React frontend with Vite, Tailwind, API client"
```

---

### Task 8: Auth Pages & Layout

**Files:**
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/context/AuthContext.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create AuthContext with login/logout/user state**

- Store tokens in localStorage
- Provide `login(username, password)`, `logout()`, `user` state
- On mount, try to decode existing token to restore session

**Step 2: Create Login page**

- Simple form: username + password fields + submit button
- On success, store tokens, redirect to dashboard
- Full-screen centered card

**Step 3: Create Layout component**

```
┌────────┬──────────────────────────────┐
│Sidebar │  <Outlet />                  │
│        │                              │
└────────┴──────────────────────────────┘
```

**Step 4: Create Sidebar component**

- Dashboard link (always)
- Dynamic agent list (from API)
- [+] New Agent button
- Settings link
- Admin Panel link (if user.role === "admin")
- Responsive: collapsible on mobile

**Step 5: Set up React Router in App.tsx**

```typescript
<Routes>
  <Route path="/login" element={<Login />} />
  <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
    <Route path="/" element={<Dashboard />} />
    <Route path="/agents/:id" element={<AgentDetail />} />
    <Route path="/agents/new" element={<AgentBuilder />} />
    <Route path="/projects/:id" element={<ProjectDetail />} />
    <Route path="/research/:id" element={<ResearchChat />} />
    <Route path="/learning/:agentId" element={<LearningDetail />} />
    <Route path="/learning/course/:id" element={<CourseChat />} />
    <Route path="/social/:agentId" element={<SocialMedia />} />
    <Route path="/settings" element={<Settings />} />
    <Route path="/admin" element={<AdminPanel />} />
  </Route>
</Routes>
```

**Step 6: Verify login flow works end-to-end**

Run: Backend + frontend dev servers
Expected: Login → redirects to dashboard → sidebar shows

**Step 7: Commit**

```bash
git commit -m "feat: add auth pages, layout, sidebar, routing"
```

---

### Task 9: Dashboard Page

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/api/agents.ts`

**Step 1: Create agents API hooks**

```typescript
// src/api/agents.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

export function useAgents() {
  return useQuery({ queryKey: ['agents'], queryFn: () => api.get('/agents').then(r => r.data) });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.post('/agents', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}
```

**Step 2: Create Dashboard page**

- Grid of agent cards showing: name, type icon, status, project/session count
- Active tasks summary across all agents
- Links to each agent detail

**Step 3: Verify dashboard loads with agents**

**Step 4: Commit**

```bash
git commit -m "feat: add dashboard page with agent overview"
```

---

### Task 10: Agent Builder Page

**Files:**
- Create: `frontend/src/pages/AgentBuilder.tsx`

**Step 1: Create AgentBuilder page**

- Template selection grid: Coding, Research, Learning, Social Media icons
- "or Create Custom Agent" option
- On template select: pre-fill form with template defaults, allow editing
- Form fields: name, model (dropdown), identity (textarea), tools (checkboxes), global rules (textarea)
- MCP servers (for custom agents)
- Submit → POST /agents → redirect to agent detail

**Step 2: Verify creating agent from template works**

**Step 3: Commit**

```bash
git commit -m "feat: add agent builder with pre-built templates"
```

---

## Phase 3: Coding Agent

### Task 11: Project CRUD API

**Files:**
- Create: `backend/app/api/projects.py`
- Test: `backend/tests/test_projects.py`

**Step 1: Write failing tests**

```python
def test_create_project(auth_client, coding_agent_id):
    response = auth_client.post(f"/agents/{coding_agent_id}/projects", json={
        "name": "E-shop",
        "description": "Build an e-shop with Next.js and Stripe",
        "architecture": "Monorepo, /app frontend, /api backend",
    })
    assert response.status_code == 201
    assert response.json()["status"] == "created"
    assert response.json()["workspace_path"].endswith("/eshop")

def test_start_project(auth_client, project_id):
    response = auth_client.post(f"/projects/{project_id}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_stop_project(auth_client, project_id):
    auth_client.post(f"/projects/{project_id}/start")
    response = auth_client.post(f"/projects/{project_id}/stop")
    assert response.status_code == 200
```

**Step 2: Implement api/projects.py**

On project creation:
1. Generate slug from name
2. Create workspace dir: `/data/users/{username}/projects/{slug}/`
3. Create `.claude/CLAUDE.md` with project-specific rules
4. Create `.nanobot/` dir with config derived from agent template
5. Set tmux_session name: `{username}-{slug}`

On project start:
1. Create tmux session
2. Start `claude` in tmux session
3. Spawn nanobot control loop subprocess
4. Create AgentInstance record
5. Update project status to "running"

On project stop:
1. Kill nanobot subprocess
2. Optionally kill tmux session
3. Update status

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git commit -m "feat: add project CRUD and lifecycle management"
```

---

### Task 12: Coding Agent Control Loop

**Files:**
- Create: `backend/app/services/coding_agent.py`
- Test: `backend/tests/test_coding_agent.py`

**Step 1: Implement CodingAgentLoop class**

```python
import asyncio
import json
from app.services.tmux import TmuxManager

class CodingAgentLoop:
    """Control loop: nanobot manages Claude Code via tmux."""

    def __init__(self, project_id: int, tmux_session: str, workspace: str, agent_config: dict):
        self.project_id = project_id
        self.tmux_session = tmux_session
        self.workspace = workspace
        self.agent_config = agent_config
        self.tmux = TmuxManager()
        self.running = False
        self.error_count = 0
        self.max_retries = 3

    async def start(self):
        """Main control loop."""
        self.running = True

        # Start Claude Code in tmux
        self.tmux.send_keys(self.tmux_session, f"cd {self.workspace} && claude")
        await asyncio.sleep(5)  # Wait for Claude Code to initialize

        while self.running:
            step = self._get_current_step()
            if not step:
                # All steps done
                self._mark_project_completed()
                break

            # 1. Send task
            prompt = self._compose_prompt(step)
            self.tmux.send_keys(self.tmux_session, prompt)

            # 2. Monitor
            result = await self._monitor_until_done()

            # 3. Evaluate
            evaluation = await self._evaluate_output(result, step)

            # 4. Next action
            if evaluation["status"] == "complete":
                self._mark_step_done(step)
                self.error_count = 0
            elif evaluation["status"] == "error":
                self.error_count += 1
                if self.error_count >= self.max_retries:
                    await self._try_alternative_approach(step)
                else:
                    self.tmux.send_keys(self.tmux_session, evaluation["fix_prompt"])
            elif evaluation["status"] == "escalate":
                self._escalate_to_ui(step, evaluation["reason"])
                break

    async def _monitor_until_done(self, timeout: int = 300) -> str:
        """Poll tmux output until Claude Code finishes."""
        elapsed = 0
        last_output = ""
        while elapsed < timeout:
            output = self.tmux.capture_pane(self.tmux_session)
            if self._claude_code_waiting_for_input(output):
                return output
            if output == last_output:
                elapsed += 2
            else:
                elapsed = 0
                last_output = output
            await asyncio.sleep(2)
        return output  # Timeout

    def _claude_code_waiting_for_input(self, output: str) -> bool:
        """Detect if Claude Code is waiting for next input."""
        lines = output.strip().split("\n")
        if not lines:
            return False
        last = lines[-1].strip()
        return last.endswith(">") or last.endswith("❯") or "?" in last

    async def stop(self):
        self.running = False
```

Note: The `_evaluate_output` method will use nanobot's AgentLoop to send the Claude Code output to GPT 5.3 Codex for analysis. The `_compose_prompt` method combines global rules + project config + step details.

**Step 2: Write basic test for control loop initialization**

**Step 3: Commit**

```bash
git commit -m "feat: add coding agent control loop"
```

---

### Task 13: Project WebSocket Endpoints

**Files:**
- Create: `backend/app/api/ws.py`

**Step 1: Implement WebSocket endpoints for live streaming**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.tmux import TmuxManager
import asyncio

router = APIRouter()
tmux = TmuxManager()

@router.websocket("/ws/project/{project_id}/terminal")
async def project_terminal(websocket: WebSocket, project_id: int):
    await websocket.accept()
    # Get tmux session name from project
    session_name = get_project_tmux_session(project_id)
    try:
        while True:
            output = tmux.capture_pane(session_name)
            await websocket.send_text(output)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@router.websocket("/ws/project/{project_id}/logs")
async def project_logs(websocket: WebSocket, project_id: int):
    await websocket.accept()
    last_id = 0
    try:
        while True:
            logs = get_new_logs(project_id, after_id=last_id)
            for log in logs:
                await websocket.send_json(log)
                last_id = log["id"]
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
```

**Step 2: Commit**

```bash
git commit -m "feat: add WebSocket endpoints for terminal and log streaming"
```

---

### Task 14: Coding Agent Frontend

**Files:**
- Create: `frontend/src/pages/CodingAgentDetail.tsx`
- Create: `frontend/src/pages/ProjectDetail.tsx`
- Create: `frontend/src/components/Terminal.tsx`
- Create: `frontend/src/components/ProjectCard.tsx`
- Create: `frontend/src/components/ImplementationPlan.tsx`

**Step 1: Create CodingAgentDetail page**

- Global rules editor (textarea, save button)
- Project list with status/progress
- [+ New Project] button → modal with name, description, architecture fields

**Step 2: Create ProjectDetail page with tabs**

Tabs: Terminal | Logs | Description | Architecture

- Terminal tab: xterm.js connected via WebSocket
- Logs tab: live log stream
- Description tab: editable project goal
- Architecture tab: editable architecture doc
- Header: project name, status badge, Start/Stop/Restart buttons
- Implementation plan sidebar: steps with checkmarks

**Step 3: Create Terminal component with xterm.js**

```typescript
import { useEffect, useRef } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from '@xterm/addon-fit';

export function Terminal({ projectId }: { projectId: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const term = new XTerm({ theme: { background: '#1e1e1e' } });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(ref.current!);
    fit.fit();

    const ws = new WebSocket(`ws://${location.host}/ws/project/${projectId}/terminal`);
    ws.onmessage = (e) => { term.clear(); term.write(e.data); };

    return () => { ws.close(); term.dispose(); };
  }, [projectId]);

  return <div ref={ref} className="h-full w-full" />;
}
```

**Step 4: Verify full flow: create project → start → see terminal**

**Step 5: Commit**

```bash
git commit -m "feat: add coding agent UI with terminal and project management"
```

---

## Phase 4: Research Agent

### Task 15: Research Session API

**Files:**
- Create: `backend/app/api/research.py`
- Test: `backend/tests/test_research.py`

**Step 1: Write failing tests**

```python
def test_create_research_session(auth_client, research_agent_id):
    response = auth_client.post(f"/agents/{research_agent_id}/research", json={
        "name": "Next.js hosting",
    })
    assert response.status_code == 201

def test_list_research_sessions(auth_client, research_agent_id):
    response = auth_client.get(f"/agents/{research_agent_id}/research")
    assert response.status_code == 200

def test_resume_research_session(auth_client, research_session_id):
    response = auth_client.post(f"/research/{research_session_id}/resume")
    assert response.status_code == 200
```

**Step 2: Implement api/research.py**

On create research session:
1. Generate slug
2. Create workspace: `/data/users/{user}/research/{slug}/`
3. Create tmux session: `{username}-research-{slug}`
4. Start `claude` with research system prompt in that tmux session
5. Return session details

On send message:
1. Store message in chat_messages
2. `tmux send-keys` the message to Claude Code
3. Monitor output, return response

On resume:
1. Check if tmux session exists
2. If not, create new tmux session and run `claude --resume` in the workspace
3. Return session details

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git commit -m "feat: add research session API with Claude Code integration"
```

---

### Task 16: Research Agent Frontend

**Files:**
- Create: `frontend/src/pages/ResearchAgentDetail.tsx`
- Create: `frontend/src/pages/ResearchChat.tsx`
- Create: `frontend/src/components/ChatInterface.tsx`

**Step 1: Create ChatInterface reusable component**

- Message list (scrollable, auto-scroll to bottom)
- Input field + send button
- WebSocket connection for real-time streaming
- Markdown rendering for messages

**Step 2: Create ResearchAgentDetail page**

- List of research sessions with status
- [+ New Research] button → creates session → redirects to chat

**Step 3: Create ResearchChat page**

- ChatInterface connected to `/ws/research/{id}/chat`
- Session name in header
- Back button to agent detail

**Step 4: Verify full flow: create research → chat → get response**

**Step 5: Commit**

```bash
git commit -m "feat: add research agent UI with chat interface"
```

---

## Phase 5: Learning Agent

### Task 17: Learning API (Subjects + Courses)

**Files:**
- Create: `backend/app/api/learning.py`
- Create: `backend/app/services/learning_agent.py`
- Test: `backend/tests/test_learning.py`

**Step 1: Write failing tests**

```python
def test_create_subject(auth_client, learning_agent_id):
    response = auth_client.post(f"/agents/{learning_agent_id}/subjects", json={
        "name": "Angličtina",
    })
    assert response.status_code == 201

def test_create_course(auth_client, subject_id):
    response = auth_client.post(f"/subjects/{subject_id}/courses", json={
        "name": "Konverzace",
        "instructions": "Practice English conversation at B1 level.",
    })
    assert response.status_code == 201

def test_send_message_to_course(auth_client, course_id):
    response = auth_client.post(f"/courses/{course_id}/message", json={
        "content": "Let's practice ordering food.",
    })
    assert response.status_code == 200
    assert response.json()["role"] == "assistant"
```

**Step 2: Implement api/learning.py**

On create subject:
1. Create dir: `/data/users/{user}/learning/{subject_slug}/`

On create course:
1. Create dir: `/data/users/{user}/learning/{subject_slug}/{course_slug}/`
2. Create empty `chat_history.json` and `student_notes.md`

On send message:
1. Load chat history + student notes
2. Compose system prompt: agent identity + course instructions + student notes
3. Call LLM (via nanobot or direct API) with history + new message
4. Save response to chat history
5. Agent updates student_notes.md if needed
6. Return response

**Step 3: Implement learning_agent.py**

Service that handles LLM calls for learning agent:
- Builds context from student_notes.md + chat history
- Calls configured model
- Parses response, detects if student_notes should be updated

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat: add learning agent API with subjects, courses, student tracking"
```

---

### Task 18: Learning Agent Frontend

**Files:**
- Create: `frontend/src/pages/LearningAgentDetail.tsx`
- Create: `frontend/src/pages/CourseChat.tsx`

**Step 1: Create LearningAgentDetail page**

- Sidebar: list of subjects, each expandable to show courses
- [+ New Subject] button
- Within each subject: [+ New Course] button
- Course creation: name + instructions textarea

**Step 2: Create CourseChat page**

- Reuse ChatInterface component
- Header: subject name > course name
- Chat connected to `/ws/course/{id}/chat` or REST polling

**Step 3: Verify full flow: create subject → course → chat → check student_notes.md updates**

**Step 4: Commit**

```bash
git commit -m "feat: add learning agent UI with subject/course hierarchy"
```

---

## Phase 6: Social Media Manager

### Task 19: Social Media API Integration

**Files:**
- Create: `backend/app/services/social_media.py`
- Create: `backend/app/api/social.py`
- Test: `backend/tests/test_social.py`

**Step 1: Implement social_media.py service**

```python
import httpx

class InstagramService:
    BASE_URL = "https://graph.instagram.com/v21.0"

    def __init__(self, access_token: str):
        self.token = access_token
        self.client = httpx.AsyncClient()

    async def get_media(self) -> list:
        """Get user's posts with metrics."""
        resp = await self.client.get(
            f"{self.BASE_URL}/me/media",
            params={
                "fields": "id,caption,media_type,media_url,thumbnail_url,timestamp,like_count,comments_count",
                "access_token": self.token,
            },
        )
        return resp.json().get("data", [])

    async def get_stories(self) -> list:
        """Get user's stories."""
        resp = await self.client.get(
            f"{self.BASE_URL}/me/stories",
            params={
                "fields": "id,media_type,media_url,timestamp",
                "access_token": self.token,
            },
        )
        return resp.json().get("data", [])

    async def publish_post(self, image_url: str, caption: str) -> dict:
        """Publish a post to Instagram."""
        # Step 1: Create media container
        container = await self.client.post(
            f"{self.BASE_URL}/me/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.token,
            },
        )
        container_id = container.json()["id"]
        # Step 2: Publish
        result = await self.client.post(
            f"{self.BASE_URL}/me/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self.token,
            },
        )
        return result.json()

class FacebookService:
    BASE_URL = "https://graph.facebook.com/v21.0"

    def __init__(self, access_token: str, page_id: str):
        self.token = access_token
        self.page_id = page_id
        self.client = httpx.AsyncClient()

    async def get_posts(self) -> list:
        resp = await self.client.get(
            f"{self.BASE_URL}/{self.page_id}/posts",
            params={
                "fields": "id,message,created_time,likes.summary(true),comments.summary(true)",
                "access_token": self.token,
            },
        )
        return resp.json().get("data", [])

    async def publish_post(self, message: str, image_url: str = None) -> dict:
        params = {"message": message, "access_token": self.token}
        if image_url:
            params["url"] = image_url
            endpoint = f"{self.BASE_URL}/{self.page_id}/photos"
        else:
            endpoint = f"{self.BASE_URL}/{self.page_id}/feed"
        resp = await self.client.post(endpoint, params=params)
        return resp.json()
```

**Step 2: Implement api/social.py**

- `GET /social/feed` — get posts from connected IG + FB
- `GET /social/stories` — get stories
- `POST /social/posts` — publish to IG/FB/both
- `GET /social/comments` — get comments
- `POST /social/comments/{id}/reply` — reply
- `GET /social/dms` — get DMs
- `POST /social/dms/{id}/reply` — reply to DM
- `POST /social/connect/instagram` — OAuth flow initiation
- `GET /social/callback/instagram` — OAuth callback
- `POST /social/ai/chat` — AI assistant for content

**Step 3: Commit**

```bash
git commit -m "feat: add Instagram/Facebook Graph API integration"
```

---

### Task 20: Social Media Frontend

**Files:**
- Create: `frontend/src/pages/SocialMediaDetail.tsx`
- Create: `frontend/src/components/social/Feed.tsx`
- Create: `frontend/src/components/social/Stories.tsx`
- Create: `frontend/src/components/social/PostComposer.tsx`
- Create: `frontend/src/components/social/Inbox.tsx`
- Create: `frontend/src/components/social/AiAssistant.tsx`

**Step 1: Create SocialMediaDetail with sub-navigation**

Tabs: Feed | Stories | New Post | DMs & Comments | AI Assistant

**Step 2: Create Feed component**

- Grid/list of posts with image, caption, metrics (likes, comments, reach)
- Platform badge (IG/FB)

**Step 3: Create PostComposer component**

- Image/video upload
- Caption textarea
- Hashtag suggestions (from AI)
- Platform toggles: Instagram ☑ Facebook ☑
- Preview
- Publish button

**Step 4: Create Inbox component**

- Two columns: comments | DMs
- Reply inline

**Step 5: Create AiAssistant component**

- Reuse ChatInterface
- "Write a post about X" → generates text + hashtags
- Copy to PostComposer button

**Step 6: Verify full flow: connect IG → view feed → create post → publish**

**Step 7: Commit**

```bash
git commit -m "feat: add social media manager UI"
```

---

## Phase 7: Admin & Settings

### Task 21: Admin Panel

**Files:**
- Create: `frontend/src/pages/AdminPanel.tsx`

**Step 1: Create AdminPanel page**

- User table: username, role, agent count, created date, [Delete] button
- Create user form: username + password fields + [Create] button
- Only visible to admin (role check in routing + sidebar)

**Step 2: Wire up to existing /users API**

**Step 3: Commit**

```bash
git commit -m "feat: add admin panel for user management"
```

---

### Task 22: Settings Page

**Files:**
- Create: `frontend/src/pages/Settings.tsx`
- Create: `backend/app/api/settings.py`

**Step 1: Create Settings page**

- API Keys section: add/remove provider keys (OpenAI, Anthropic, etc.)
- Keys are masked in UI (show last 4 chars)
- Connected social accounts section

**Step 2: Implement api/settings.py**

- `GET /settings/api-keys` — list providers (masked keys)
- `POST /settings/api-keys` — add/update key (encrypted storage)
- `DELETE /settings/api-keys/{id}` — remove key

**Step 3: Commit**

```bash
git commit -m "feat: add settings page with API key management"
```

---

## Phase 8: PWA & Deployment

### Task 23: PWA Setup

**Files:**
- Modify: `frontend/vite.config.ts`
- Create: `frontend/public/manifest.json`
- Create: `frontend/src/sw.ts`

**Step 1: Install vite-plugin-pwa**

```bash
cd frontend && npm install vite-plugin-pwa -D
```

**Step 2: Configure PWA in vite.config.ts**

```typescript
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'AutoCode',
        short_name: 'AutoCode',
        theme_color: '#1e1e1e',
        background_color: '#1e1e1e',
        display: 'standalone',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
});
```

**Step 3: Add PWA icons**

Generate 192x192 and 512x512 icons for AutoCode.

**Step 4: Verify PWA installs in Chrome**

**Step 5: Commit**

```bash
git commit -m "feat: configure PWA with service worker and manifest"
```

---

### Task 24: Deployment Configuration

**Files:**
- Create: `Caddyfile`
- Create: `deploy/autocode.service` (systemd)
- Create: `deploy/install.sh`

**Step 1: Create Caddyfile**

```
autocode.example.com {
    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle /ws/* {
        reverse_proxy localhost:8000
    }
    handle {
        root * /opt/autocode/frontend/dist
        file_server
        try_files {path} /index.html
    }
}
```

**Step 2: Create systemd service**

```ini
[Unit]
Description=AutoCode Backend
After=network.target

[Service]
Type=simple
User=autocode
WorkingDirectory=/opt/autocode/backend
ExecStart=/opt/autocode/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
Environment=AUTOCODE_SECRET_KEY=generate-a-real-key
Environment=AUTOCODE_DATA_DIR=/data/users

[Install]
WantedBy=multi-user.target
```

**Step 3: Create install.sh script**

```bash
#!/bin/bash
# Install AutoCode on VPS
set -e

# Create directories
mkdir -p /opt/autocode /data/users
useradd -r -s /usr/sbin/nologin autocode || true

# Install system dependencies
apt install -y tmux python3.11 python3.11-venv nodejs npm

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Backend
cd /opt/autocode
git clone <repo> .
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e .

# Frontend
cd ../frontend
npm install
npm run build

# Systemd
cp deploy/autocode.service /etc/systemd/system/
systemctl enable --now autocode

# Caddy
cp Caddyfile /etc/caddy/Caddyfile
systemctl reload caddy

echo "AutoCode installed! Set your domain in /etc/caddy/Caddyfile"
```

**Step 4: Commit**

```bash
git commit -m "feat: add deployment config (Caddy, systemd, install script)"
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1. Backend Foundation | 1-6 | FastAPI, DB, auth, users, agents CRUD, tmux manager |
| 2. Frontend Foundation | 7-10 | React app, routing, layout, dashboard, agent builder |
| 3. Coding Agent | 11-14 | Project management, control loop, terminal, live logs |
| 4. Research Agent | 15-16 | Research sessions, chat over Claude Code, resume |
| 5. Learning Agent | 17-18 | Subjects, courses, tutor AI, student notes |
| 6. Social Media | 19-20 | IG/FB integration, feed, post composer, AI assistant |
| 7. Admin & Settings | 21-22 | User management, API keys |
| 8. PWA & Deployment | 23-24 | Installable PWA, VPS deployment |
