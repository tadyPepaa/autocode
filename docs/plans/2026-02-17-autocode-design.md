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
│  └── Tmux Manager (session lifecycle)                │
│                                                      │
│  SQLite database                                     │
│  Filesystem: /data/users/{username}/projects/        │
│  Tmux: {username}-{project-name} sessions            │
└─────────────────────────────────────────────────────┘
         │
         │ subprocess per agent instance
         ▼
┌─────────────────────────────────────────────────────┐
│              Nanobot Instances                        │
│                                                      │
│  Each instance = isolated subprocess with:           │
│  ├── Own AgentLoop (nanobot-ai)                      │
│  ├── Own config (model, identity, tools)             │
│  ├── Own workspace directory                         │
│  ├── Own memory files (MEMORY.md, HISTORY.md)        │
│  └── Own tmux session (if applicable)                │
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
| Agent Framework | nanobot-ai (as library) |
| Agent LLM | Configurable per agent (GPT 5.3 Codex, Claude Opus 4.6, etc.) |
| Process Management | Python subprocess + tmux |
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
model: str (e.g. "openai/gpt-5.3-codex")
identity: text (behavior rules, IDENTITY.md content)
tools: json (list of enabled tools)
mcp_servers: json (MCP server configs)
workspace_base: str (base directory for instances)
global_rules: text (shared rules across all instances)
created_at: datetime
```

### projects (agent instances for coding agent)
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

### agent_instances (running instances)
```
id: int (PK)
user_id: int (FK users)
agent_id: int (FK agents)
project_id: int (FK projects, nullable — non-project agents)
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

### Agent Instances

When a project starts (or a non-project agent is activated), a **subprocess** is spawned from the template:
- Own nanobot AgentLoop with template config
- Own workspace directory
- Own memory files
- Fully isolated from other instances

### Coding Agent — Control Loop

The coding agent's core loop for managing Claude Code:

```
1. SEND TASK
   - Read current step from implementation_plan
   - Compose prompt with project context
   - tmux send-keys to Claude Code session

2. MONITOR (poll every 2 seconds)
   - tmux capture-pane to read output
   - Detect: waiting for input / error / asking confirmation
   - Stream output to web UI via WebSocket

3. EVALUATE
   - Nanobot (GPT 5.3) analyzes Claude Code output
   - Decides: task complete / needs fix / needs different approach

4. NEXT ACTION
   - Complete → mark step done, send next step
   - Error → send fix instructions
   - Stuck (3x same error) → try different approach
   - Still stuck → escalate to web UI ("needs help")

5. ALL STEPS DONE → mark project as completed
```

### Edge Case Handling

| Situation | Response |
|-----------|----------|
| Claude Code session crashes | Detect via `tmux has-session`, restart, resend last task |
| No output for >5 min | Timeout → Ctrl+C, ask what happened, optionally restart |
| Claude Code asks for decision | Nanobot decides based on project context |
| Repeated error (3x) | Try alternative approach or escalate |
| Context window full | Detect compression, send state summary, continue |

### Layered Configuration

```
Global agent rules (shared across all projects of this agent type):
  ~/.autocode/agents/{agent-id}/RULES.md
  Managed via web UI "Global Rules" editor on agent detail page

Project-specific config:
  /data/users/{user}/projects/{project}/.claude/CLAUDE.md
  Contains: tech stack, project conventions, specific instructions

Nanobot identity (per instance):
  = Global RULES.md + Project CLAUDE.md + Project description + Architecture + Plan
```

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

### Pages

**Dashboard** — overview of all agents, their status, active tasks across all projects.

**Agent Detail** — agent config, global rules editor, list of projects/instances with status, [+ New Project] button.

**Project Detail** — project goal, architecture, implementation plan with step progress, live log stream, tabs:
- Terminal (xterm.js — live Claude Code session via WebSocket)
- Logs (structured agent decision log)
- Description (editable project goal)
- Architecture (editable architecture document)

**Agent Builder** — form to create new agent: name, model, identity/rules, tool selection, MCP servers.

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
3. Creates subdirs: `projects/`, `config/`
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

### Projects
- `GET /agents/{id}/projects` — list projects for agent
- `POST /agents/{id}/projects` — create project
- `GET /projects/{id}` — project detail
- `PUT /projects/{id}` — update project
- `DELETE /projects/{id}` — delete project + cleanup
- `POST /projects/{id}/start` — start agent instance
- `POST /projects/{id}/stop` — stop agent instance
- `POST /projects/{id}/restart` — restart agent instance

### WebSocket
- `WS /ws/project/{id}/logs` — live log stream
- `WS /ws/project/{id}/terminal` — xterm.js terminal (tmux capture-pane stream)

---

## Filesystem Layout

```
/data/
  users/
    tomas/
      config/
        api_keys.json (encrypted)
      projects/
        eshop/
          .claude/CLAUDE.md
          .nanobot/
            config.json
            IDENTITY.md
            MEMORY.md
            HISTORY.md
          src/
          ...
        deploy-cli/
          ...
    lucka/
      config/
      projects/
        blog/
          ...

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

## Future Extensibility

- More agent types (research, devops, assistant) — just create via Agent Builder
- Agent-to-agent communication (one agent delegates to another)
- Notification system (Telegram/email when project completes or needs help)
- Project templates (predefined stacks/architectures)
- Cost tracking (LLM API usage per project/user)
