# AutoCode — Agent Manager Platform

## Overview

Web application (PWA) for managing multiple independent AI agents (nanobots). Each agent is fully configurable — model, behavior rules, tools. Primary use case: coding agent that autonomously manages Claude Code sessions via tmux, implementing entire projects from a high-level description.

## Target Users

Private/family use. Admin (owner) creates accounts for family members. Each user has independent agents, projects, and workspaces. Deployed on VPS.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React PWA (frontend)                │
│  ├── Dashboard                                       │
│  ├── Agent detail (per agent type)                   │
│  ├── Project detail (per project)                    │
│  ├── Agent Builder (create/edit agents)              │
│  ├── Admin Panel (user management)                   │
│  └── Settings                                        │
└────────────────────────┬────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────┼────────────────────────────┐
│                   FastAPI Backend                     │
│                                                      │
│  ├── Auth (JWT, username/password)                   │
│  ├── REST API (agents, projects, users CRUD)         │
│  ├── WebSocket (live log stream, xterm.js terminal)  │
│  ├── Agent Orchestrator (subprocess management)      │
│  ├── Tmux Manager (session lifecycle)                │
│  └── Social Media API integration (IG/FB Graph API)  │
│                                                      │
│  SQLite database                                     │
│  Filesystem: /data/users/{username}/                 │
│  Tmux: {username}-{session-name} sessions            │
└─────────────────────────────────────────────────────┘
         │
         │ subprocess per agent instance
         ▼
┌─────────────────────────────────────────────────────┐
│              Agent Instances                          │
│                                                      │
│  Coding Agent: nanobot subprocess → tmux → claude    │
│  Research Agent: claude code session (chat)           │
│  Learning Agent: nanobot subprocess (direct AI)       │
│  Social Media: web app + AI chat assistant            │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| PWA | vite-plugin-pwa (Workbox) |
| Terminal | xterm.js (react wrapper) |
| Backend | FastAPI (Python 3.11+) |
| Auth | JWT (short-lived access + refresh token) |
| Database | SQLite (SQLModel ORM) |
| Agent Framework | nanobot-ai (as library, for coding + learning agents) |
| Agent LLM | Configurable per agent (GPT 5.3 Codex, Claude Opus 4.6, etc.) |
| Process Management | Python subprocess + tmux |
| Social Media | Instagram Graph API + Facebook Graph API |
| Reverse Proxy | Caddy (auto TLS) |

---

## Data Model

### users
```
id: int (PK)
username: str (unique)
password_hash: str
role: str ("admin" | "user")
created_at: datetime
```

### agents (templates)
```
id: int (PK)
user_id: int (FK users)
name: str
type: str ("coding" | "research" | "learning" | "social_media" | "custom")
model: str (e.g. "openai/gpt-5.3-codex")
identity: text (behavior rules, IDENTITY.md content)
tools: json (list of enabled tools)
mcp_servers: json (MCP server configs)
global_rules: text (shared rules across all instances)
created_at: datetime
```

### projects (coding agent instances)
```
id: int (PK)
user_id: int (FK users)
agent_id: int (FK agents)
name: str
slug: str (filesystem-safe name)
description: text (project goal)
architecture: text (optional, requested architecture)
implementation_plan: json (steps with status)
status: str ("created" | "planning" | "running" | "paused" | "completed" | "failed")
current_step: int
tmux_session: str (tmux session name)
workspace_path: str (absolute path)
created_at: datetime
updated_at: datetime
```

### research_sessions (research agent)
```
id: int (PK)
user_id: int (FK users)
agent_id: int (FK agents)
name: str
slug: str
status: str ("active" | "archived")
tmux_session: str (tmux session name for claude code)
workspace_path: str
created_at: datetime
updated_at: datetime
```

### learning_subjects (learning agent — folders)
```
id: int (PK)
user_id: int (FK users)
agent_id: int (FK agents)
name: str (e.g. "Angličtina")
created_at: datetime
```

### learning_courses (learning agent — sessions within subject)
```
id: int (PK)
user_id: int (FK users)
subject_id: int (FK learning_subjects)
name: str (e.g. "Konverzace")
instructions: text (custom instructions for this course)
chat_history_path: str (path to chat_history.json)
student_notes_path: str (path to student_notes.md)
created_at: datetime
updated_at: datetime
```

### social_accounts (social media agent)
```
id: int (PK)
user_id: int (FK users)
agent_id: int (FK agents)
platform: str ("instagram" | "facebook")
access_token: str (encrypted)
account_name: str
created_at: datetime
```

### chat_messages (shared for research + learning + social AI chat)
```
id: int (PK)
user_id: int (FK users)
session_type: str ("research" | "learning" | "social_ai")
session_id: int (FK to respective session table)
role: str ("user" | "assistant")
content: text
created_at: datetime
```

### agent_instances (running instances)
```
id: int (PK)
user_id: int (FK users)
agent_id: int (FK agents)
project_id: int (FK projects, nullable)
pid: int (OS process ID)
status: str ("running" | "stopped" | "crashed")
started_at: datetime
stopped_at: datetime
```

### logs
```
id: int (PK)
project_id: int (FK projects, nullable)
agent_instance_id: int (FK agent_instances)
level: str ("info" | "action" | "error" | "agent_decision")
message: text
timestamp: datetime
```

### api_keys
```
id: int (PK)
user_id: int (FK users)
provider: str ("openai" | "anthropic" | etc.)
encrypted_key: str
created_at: datetime
```

---

## Agent System

### Agent as Template

An agent is a **template** (type definition), not a running instance. It defines:
- Model to use
- Identity/behavior rules
- Available tools
- Global rules shared across all instances

Users create agents from pre-built templates or build custom ones via Agent Builder.

### Agent Instances

When a project/session starts, a **subprocess** is spawned from the template:
- Own config derived from template
- Own workspace directory
- Own memory/history files
- Fully isolated from other instances

---

## Agent Details

### 1. Coding Agent

**How it works**: Nanobot (GPT 5.3 Codex) autonomously manages Claude Code (Opus 4.6) via tmux.

**Architecture**:
- Each project = own subprocess + own tmux session + own workspace
- Nanobot composes prompts and sends to Claude Code via `tmux send-keys`
- Monitors output via `tmux capture-pane` (polling every 2s)
- Evaluates results and decides next action

**Control Loop**:
```
1. SEND TASK — read current step, compose prompt, tmux send-keys
2. MONITOR — capture-pane polling, stream to web UI via WebSocket
3. EVALUATE — nanobot analyzes output, decides: complete / fix / retry
4. NEXT ACTION — mark step done + next task / send fix / escalate
5. ALL STEPS DONE → project completed
```

**Task Input**: Flexible — user provides just a goal, or goal + architecture + details. Agent generates implementation plan autonomously.

**Layered Configuration**:
```
Global rules: ~/.autocode/agents/{agent-id}/RULES.md
  (shared across all projects, managed via web UI)
Project config: /data/users/{user}/projects/{project}/.claude/CLAUDE.md
  (tech stack, conventions, specific instructions)
Nanobot identity = Global RULES + Project CLAUDE.md + description + architecture + plan
```

**Edge Cases**:

| Situation | Response |
|-----------|----------|
| Claude Code session crashes | Detect via `tmux has-session`, restart, resend last task |
| No output for >5 min | Timeout → Ctrl+C, ask what happened, optionally restart |
| Claude Code asks for decision | Nanobot decides based on project context |
| Repeated error (3x) | Try alternative approach or escalate |
| Context window full | Detect compression, send state summary, continue |

**Consultation**: Nanobot (GPT 5.3) consults with Claude Code (Opus 4.6) on approaches, searches web for current best practices.

### 2. Research Agent

**How it works**: Chat interface over Claude Code. Each research = isolated Claude Code session.

**Architecture**:
- User creates "New Research" → opens empty chat
- Backend starts new tmux session with `claude` (with research system prompt)
- User types questions, Claude Code researches and responds
- Each research session is fully isolated (only knows system prompt + own conversation)
- User can return to old sessions anytime (like `claude --resume`)

**Filesystem**:
```
/data/users/{user}/research/
├── nextjs-hosting/        ← research session
│   └── (claude code session data)
├── headless-cms/
└── rust-ecosystem/
```

### 3. Learning & Tutor Agent

**How it works**: AI agent directly (nanobot, not Claude Code). Two-level hierarchy: subjects → courses.

**Architecture**:
- Subject = organizational folder (e.g. "Angličtina")
- Course = agent session with custom instructions (e.g. "Konverzace", "Gramatika", "Slovíčka")
- Each course has one continuous conversation — agent remembers everything
- Agent maintains `student_notes.md` per course — tracks what user knows, weaknesses, progress
- On each conversation start, agent reads student_notes.md to know where to continue

**Filesystem**:
```
/data/users/{user}/learning/
├── anglictina/                    ← subject
│   ├── konverzace/                ← course
│   │   ├── chat_history.json
│   │   └── student_notes.md
│   ├── gramatika/
│   │   ├── chat_history.json
│   │   └── student_notes.md
│   └── slovicka/
│       ├── chat_history.json
│       └── student_notes.md
└── python/                        ← subject
    ├── basics/
    └── async-programming/
```

**student_notes.md** (maintained by agent):
```
Level: B1
Strengths: food vocabulary, travel situations
Weaknesses: present perfect vs past simple, articles
Last lesson: ordering at restaurant
Covered: airport, hotel, restaurant
Recurring mistakes:
  - "I have been there yesterday" → "I was there yesterday"
```

### 4. Social Media Manager

**How it works**: Web app with Instagram/Facebook API integration + AI chat assistant.

**NOT an autonomous agent** — it's a social media management tool built into the platform.

**Features**:
- View own feed (posts with reach/likes/comments metrics)
- View own stories
- Create posts (text + image/video) — publish to IG only / FB only / both
- Reply to comments and DMs
- AI chat assistant — "write a post about product X" → generates text + hashtags → user edits → publishes

**API Integration**:
- Instagram Graph API (via Facebook Developer)
- Facebook Graph API
- OAuth flow to connect accounts

**UI Sections** (sub-navigation within agent):
- Feed (own posts + metrics)
- Stories (own stories)
- New Post (composer with IG/FB toggle)
- DMs/Comments (inbox)
- AI Assistant (chat for content ideas)

---

## Web UI

### Navigation (Sidebar)

```
Dashboard
────────
{Agent 1 name}
{Agent 2 name}
{Agent 3 name}
...
────────
[+] New Agent
────────
⚙ Settings          (all users)
👤 Admin Panel       (admin only)
```

Agents are dynamically added to sidebar as user creates them. Clicking an agent opens its detail page.

### Pages

**Dashboard** — overview of all agents, their status, active tasks across all projects.

**Coding Agent Detail** — global rules editor, list of projects with status/progress, [+ New Project].

**Coding Project Detail** — project goal, architecture, implementation plan with step progress, live log stream, tabs:
- Terminal (xterm.js — live Claude Code session via WebSocket)
- Logs (structured agent decision log)
- Description (editable project goal)
- Architecture (editable architecture document)

**Research Agent Detail** — list of research sessions, [+ New Research]. Click session → chat interface with Claude Code.

**Learning Agent Detail** — list of subjects, each expandable to show courses. [+ New Subject], [+ New Course]. Click course → chat interface with tutor agent.

**Social Media Agent Detail** — sub-navigation: Feed, Stories, New Post, DMs/Comments, AI Assistant.

**Agent Builder** — choose from pre-built template or create custom. Form: name, model, identity/rules, tool selection, MCP servers.

**Admin Panel** (admin only) — user list with agent count, create user form (username + password), delete user.

**Settings** — user's API keys management, personal preferences.

---

## Multi-User

### Roles

- **admin**: full access + admin panel (user CRUD)
- **user**: sees only own agents, projects, data

### User Creation Flow

Admin clicks "Create User" → enters username + password → backend:
1. Creates DB record (users table, role="user")
2. Creates workspace: `/data/users/{username}/`
3. Creates subdirs: `projects/`, `research/`, `learning/`, `config/`
4. User can log in immediately

### Isolation

| Layer | Mechanism |
|-------|-----------|
| Data | All DB queries filtered by `user_id` |
| Filesystem | `/data/users/{username}/` — each user's workspace |
| Tmux | Session prefix `{username}-` — no cross-user visibility |
| API keys | Per-user, stored encrypted in DB |
| Subprocesses | Each agent instance runs under the user's data directory |

---

## API Endpoints (Overview)

### Auth
- `POST /auth/login` — returns JWT
- `POST /auth/refresh` — refresh token

### Users (admin only)
- `GET /users` — list users
- `POST /users` — create user
- `DELETE /users/{id}` — delete user + cleanup workspace

### Agents
- `GET /agents` — list user's agents
- `POST /agents` — create agent template
- `GET /agents/{id}` — agent detail
- `PUT /agents/{id}` — update agent config
- `DELETE /agents/{id}` — delete agent + all instances

### Projects (coding agent)
- `GET /agents/{id}/projects` — list projects
- `POST /agents/{id}/projects` — create project
- `GET /projects/{id}` — project detail
- `PUT /projects/{id}` — update project
- `DELETE /projects/{id}` — delete project + cleanup
- `POST /projects/{id}/start` — start agent instance
- `POST /projects/{id}/stop` — stop agent instance
- `POST /projects/{id}/restart` — restart agent instance

### Research
- `GET /agents/{id}/research` — list research sessions
- `POST /agents/{id}/research` — create new research session
- `GET /research/{id}` — research session detail + chat history
- `DELETE /research/{id}` — delete research session
- `POST /research/{id}/resume` — resume claude code session
- `POST /research/{id}/message` — send message to claude code

### Learning
- `GET /agents/{id}/subjects` — list subjects
- `POST /agents/{id}/subjects` — create subject
- `DELETE /subjects/{id}` — delete subject
- `GET /subjects/{id}/courses` — list courses
- `POST /subjects/{id}/courses` — create course
- `GET /courses/{id}` — course detail + chat history
- `DELETE /courses/{id}` — delete course
- `POST /courses/{id}/message` — send message to tutor agent

### Social Media
- `GET /social/feed` — get own posts with metrics
- `GET /social/stories` — get own stories
- `POST /social/posts` — create and publish post
- `GET /social/comments` — get comments on posts
- `POST /social/comments/{id}/reply` — reply to comment
- `GET /social/dms` — get DM conversations
- `POST /social/dms/{id}/reply` — reply to DM
- `POST /social/ai/chat` — send message to AI assistant

### WebSocket
- `WS /ws/project/{id}/logs` — live log stream (coding agent)
- `WS /ws/project/{id}/terminal` — xterm.js terminal
- `WS /ws/research/{id}/chat` — research chat stream
- `WS /ws/course/{id}/chat` — learning chat stream

---

## Filesystem Layout

```
/data/
  users/
    tomas/
      config/
      projects/                          # coding agent
        eshop/
          .claude/CLAUDE.md
          .nanobot/
            config.json
            IDENTITY.md
            MEMORY.md
            HISTORY.md
          src/...
        deploy-cli/...
      research/                          # research agent
        nextjs-hosting/
        headless-cms/
      learning/                          # learning agent
        anglictina/
          konverzace/
            chat_history.json
            student_notes.md
          gramatika/
            chat_history.json
            student_notes.md
        python/
          basics/...
    lucka/
      config/
      projects/...
      research/...
      learning/...

/opt/autocode/
  backend/           # FastAPI app
  frontend/          # React PWA (built, served by Caddy)
  autocode.db        # SQLite database
```

---

## Deployment

Single VPS deployment:
1. Caddy as reverse proxy (auto HTTPS)
2. FastAPI backend (uvicorn, systemd service)
3. React PWA served as static files by Caddy
4. SQLite database file
5. tmux available system-wide
6. Claude Code CLI installed
7. nanobot-ai installed via pip

---

## Pre-built Agent Templates

Users can create agents from templates (one click, then customize) or build from scratch.

### 1. Coding Agent (Kodovací agent)
- **Model**: GPT 5.3 Codex (configurable)
- **Purpose**: Autonomously manages Claude Code via tmux, implements entire projects
- **Tools**: tmux, exec, read_file, write_file, web_search
- **Special**: Control loop, per-project instances, layered config

### 2. Research Agent (Výzkumný agent)
- **Model**: Claude Opus 4.6 (configurable)
- **Purpose**: Chat interface over Claude Code for web research, analysis, reports
- **Tools**: (Claude Code built-in — web search, file access)
- **Special**: Isolated sessions, resume support

### 3. Learning & Tutor Agent (Vzdělávací agent)
- **Model**: Claude Opus 4.6 (configurable)
- **Purpose**: Personalized tutor — subjects with courses, custom instructions, student progress tracking
- **Tools**: web_search, web_fetch, read_file, write_file
- **Special**: Two-level hierarchy (subject → course), student_notes.md, continuous conversation per course

### 4. Social Media Manager (Správa sociálních sítí)
- **Model**: Claude Sonnet 4.5 (configurable)
- **Purpose**: Manage Instagram + Facebook — view feed/stories, create posts, reply to comments/DMs, AI content assistant
- **Tools**: Instagram Graph API, Facebook Graph API
- **Special**: Not autonomous agent — integrated social media management tool with AI chat

### Custom Agent
Users can create fully custom agents via Agent Builder with arbitrary model, identity, tools, and MCP servers.

---

## MVP Scope

### MVP1
- Coding Agent (full)
- Research Agent (full)
- Learning Agent (full)
- Social Media Manager (full)
- Agent Builder (custom agents)
- Admin Panel (user management)
- Auth (JWT, username/password)
- PWA

### MVP2
- Personal Assistant (calendar, reminders, integrations)
- Agent-to-agent communication
- Notification system (Telegram/email)
- Cost tracking (LLM API usage)
- More pre-built templates (Finance, Email, DevOps, ...)
