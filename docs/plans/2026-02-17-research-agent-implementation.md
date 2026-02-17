# Research Agent Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the tmux-based terminal UI for research sessions with a proper chat (persisted messages with real Claude responses) and a markdown canvas (rendered .md files from the research workspace).

**Architecture:** One-shot Claude CLI calls (`claude -p` with `-c` for continuation) instead of interactive tmux sessions. Messages stored in DB. Background asyncio tasks for Claude execution. Polling-based frontend for messages and file updates.

**Tech Stack:** FastAPI + asyncio (backend), React + react-markdown + remark-gfm (frontend), existing SQLModel ChatMessage table.

---

### Task 1: Add `research_runner` service — Claude CLI wrapper

**Files:**
- Create: `backend/app/services/research_runner.py`
- Test: `backend/tests/test_research_runner.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_research_runner.py
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.research_runner import run_claude_message


@pytest.mark.asyncio
async def test_run_claude_first_message():
    """First message uses claude -p without -c flag."""
    fake_result = json.dumps({"type": "result", "result": "Hello from Claude"})
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (fake_result.encode(), b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await run_claude_message(
            workspace_path="/tmp/test",
            message="Hello",
            is_continuation=False,
        )

    assert result == "Hello from Claude"
    call_args = mock_exec.call_args[0]
    assert "-p" in call_args
    assert "Hello" in call_args
    assert "-c" not in call_args


@pytest.mark.asyncio
async def test_run_claude_continuation_message():
    """Subsequent messages use -c flag to continue conversation."""
    fake_result = json.dumps({"type": "result", "result": "Continued response"})
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (fake_result.encode(), b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await run_claude_message(
            workspace_path="/tmp/test",
            message="Continue",
            is_continuation=True,
        )

    assert result == "Continued response"
    call_args = mock_exec.call_args[0]
    assert "-c" in call_args


@pytest.mark.asyncio
async def test_run_claude_error():
    """Non-zero exit code raises RuntimeError."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"Error occurred")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="Claude CLI failed"):
            await run_claude_message("/tmp/test", "Hello", False)
```

**Step 2: Run test to verify it fails**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research_runner.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.research_runner'"

**Step 3: Write minimal implementation**

```python
# backend/app/services/research_runner.py
import asyncio
import json


async def run_claude_message(
    workspace_path: str,
    message: str,
    is_continuation: bool,
) -> str:
    """Run Claude Code CLI in one-shot mode and return the response text."""
    cmd = [
        "claude",
        "-p", message,
        "--dangerously-skip-permissions",
        "--output-format", "json",
    ]
    if is_continuation:
        cmd.append("-c")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=workspace_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"Claude CLI failed (exit {proc.returncode}): {stderr.decode()}")

    data = json.loads(stdout.decode())
    return data.get("result", "")
```

**Step 4: Run test to verify it passes**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research_runner.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add backend/app/services/research_runner.py backend/tests/test_research_runner.py
git commit -m "feat: add research_runner service for one-shot Claude CLI calls"
```

---

### Task 2: Add `GET /research/{id}/messages` endpoint

**Files:**
- Modify: `backend/app/api/research.py`
- Modify: `backend/tests/test_research.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_research.py`:

```python
def test_get_research_messages(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
    session: Session,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Messages")
    session_id = create_resp.json()["id"]

    # Add messages directly to DB
    from app.models.common import ChatMessage as ChatMessageModel

    for i, (role, content) in enumerate([
        ("user", "What is AI?"),
        ("assistant", "AI is artificial intelligence."),
        ("user", "Tell me more"),
    ]):
        msg = ChatMessageModel(
            user_id=2,  # testuser
            session_type="research",
            session_id=session_id,
            role=role,
            content=content,
        )
        session.add(msg)
    session.commit()

    resp = client.get(
        f"/api/research/{session_id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "What is AI?"
    assert data[2]["content"] == "Tell me more"


def test_get_research_messages_empty(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Empty")
    session_id = create_resp.json()["id"]

    resp = client.get(
        f"/api/research/{session_id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_research_messages_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.get(
        "/api/research/9999/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py::test_get_research_messages -v`
Expected: FAIL with 404 (endpoint doesn't exist)

**Step 3: Add endpoint to `backend/app/api/research.py`**

Add `MessageResponse` model and endpoint (same pattern as learning module):

```python
class MessageResponse(BaseModel):
    id: int
    user_id: int
    session_type: str
    session_id: int
    role: str
    content: str
    created_at: datetime


@router.get(
    "/research/{session_id}/messages",
    response_model=list[MessageResponse],
)
async def get_research_messages(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_session_or_404(session_id, user, db)
    messages = db.exec(
        select(ChatMessage)
        .where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.created_at)
    ).all()
    return messages
```

**Step 4: Run tests**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add backend/app/api/research.py backend/tests/test_research.py
git commit -m "feat: add GET /research/{id}/messages endpoint"
```

---

### Task 3: Add file listing and content endpoints

**Files:**
- Modify: `backend/app/api/research.py`
- Modify: `backend/tests/test_research.py`

**Step 1: Write the failing tests**

Add to `backend/tests/test_research.py`:

```python
def test_list_research_files(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Files Test")
    workspace = Path(create_resp.json()["workspace_path"])

    # Create some .md files
    (workspace / "research.md").write_text("# Research\n\nSome content")
    (workspace / "notes.md").write_text("# Notes")
    (workspace / "data.csv").write_text("a,b,c")  # not .md, should be excluded

    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/files",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    names = {f["name"] for f in data}
    assert "research.md" in names
    assert "notes.md" in names
    assert "data.csv" not in names


def test_list_research_files_empty(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(client, user_token, agent["id"], name="No Files")

    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/files",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_research_file_content(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Content Test")
    workspace = Path(create_resp.json()["workspace_path"])
    (workspace / "output.md").write_text("# Output\n\nHello world")

    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/file-content",
        params={"path": "output.md"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "# Output\n\nHello world"
    assert data["name"] == "output.md"


def test_get_research_file_content_traversal_blocked(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Traversal")

    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/file-content",
        params={"path": "../../etc/passwd"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 400


def test_get_research_file_content_not_found(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    mock_tmux,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Missing")

    resp = client.get(
        f"/api/research/{create_resp.json()['id']}/file-content",
        params={"path": "nonexistent.md"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py::test_list_research_files -v`
Expected: FAIL with 404

**Step 3: Add endpoints to `backend/app/api/research.py`**

```python
import os


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    modified_at: float


class FileContent(BaseModel):
    name: str
    path: str
    content: str


@router.get(
    "/research/{session_id}/files",
    response_model=list[FileInfo],
)
async def list_research_files(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)
    workspace = Path(research.workspace_path)
    if not workspace.exists():
        return []

    files = []
    for md_file in sorted(workspace.rglob("*.md")):
        # Skip hidden dirs like .claude/
        if any(part.startswith(".") for part in md_file.relative_to(workspace).parts):
            continue
        stat = md_file.stat()
        files.append(FileInfo(
            name=md_file.name,
            path=str(md_file.relative_to(workspace)),
            size=stat.st_size,
            modified_at=stat.st_mtime,
        ))

    # Sort by modified_at descending (newest first)
    files.sort(key=lambda f: f.modified_at, reverse=True)
    return files


@router.get(
    "/research/{session_id}/file-content",
    response_model=FileContent,
)
async def get_research_file_content(
    session_id: int,
    path: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)
    workspace = Path(research.workspace_path)
    target = (workspace / path).resolve()

    # Prevent directory traversal
    if not str(target).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    content = target.read_text(encoding="utf-8")
    return FileContent(
        name=target.name,
        path=path,
        content=content,
    )
```

**Step 4: Run all tests**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add backend/app/api/research.py backend/tests/test_research.py
git commit -m "feat: add research file listing and content endpoints"
```

---

### Task 4: Rewrite `create_research_session` — remove tmux, write CLAUDE.md

**Files:**
- Modify: `backend/app/api/research.py`
- Modify: `backend/tests/test_research.py`

**Step 1: Write the failing test**

Replace the `test_create_research_session` test to reflect new behavior:

```python
def test_create_research_session_new(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
):
    # Update agent identity first
    client.put(
        f"/api/agents/{agent['id']}",
        json={"identity": "You are a research expert."},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    resp = _create_research(
        client, user_token, agent["id"], name="Deep Learning Research"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Deep Learning Research"
    assert data["slug"] == "deep-learning-research"
    assert data["status"] == "idle"
    assert data["agent_id"] == agent["id"]

    # Verify workspace was created with CLAUDE.md
    workspace = Path(data["workspace_path"])
    assert workspace.exists()
    claude_md = workspace / "CLAUDE.md"
    assert claude_md.exists()
    assert "research expert" in claude_md.read_text()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py::test_create_research_session_new -v`
Expected: FAIL — status is "active" not "idle", no CLAUDE.md

**Step 3: Rewrite `create_research_session` in `backend/app/api/research.py`**

Remove tmux logic, add CLAUDE.md creation:

```python
@router.post(
    "/agents/{agent_id}/research",
    response_model=ResearchSessionResponse,
    status_code=201,
)
async def create_research_session(
    agent_id: int,
    body: CreateResearchRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agent = _get_agent_or_404(agent_id, user, db)

    slug = _generate_slug(body.name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid session name")

    workspace = Path(settings.data_dir) / user.username / "research" / slug
    workspace.mkdir(parents=True, exist_ok=True)

    # Write agent identity to CLAUDE.md
    claude_md = workspace / "CLAUDE.md"
    identity = agent.identity or "You are a research assistant."
    claude_md.write_text(identity, encoding="utf-8")

    research = ResearchSession(
        user_id=user.id,
        agent_id=agent_id,
        name=body.name,
        slug=slug,
        status="idle",
        tmux_session="",
        workspace_path=str(workspace),
    )
    db.add(research)
    db.commit()
    db.refresh(research)
    return research
```

**Step 4: Update existing tests that depend on old behavior**

Many existing tests use `mock_tmux` fixture and assert `status == "active"`. These need updating:

- `test_create_research_session` → replaced by `test_create_research_session_new`
- `test_create_research_tmux_naming` → delete (no more tmux)
- Tests that use `mock_tmux` for create → remove `mock_tmux` dependency from create-only tests
- Tests asserting `status == "active"` → change to `status == "idle"`

Update `_create_research` helper: remove `mock_tmux` from tests that only create sessions.

**Step 5: Run all research tests**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add backend/app/api/research.py backend/tests/test_research.py
git commit -m "refactor: remove tmux from research session creation, write CLAUDE.md"
```

---

### Task 5: Rewrite `send_message` — async Claude CLI execution

**Files:**
- Modify: `backend/app/api/research.py`
- Modify: `backend/tests/test_research.py`

**Step 1: Write the failing test**

```python
@patch("app.api.research.run_claude_message")
def test_send_message_new(
    mock_claude: MagicMock,
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    session: Session,
):
    # Make mock return a coroutine
    mock_claude.return_value = "Claude says hello"

    create_resp = _create_research(client, user_token, agent["id"], name="Chat New")
    session_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/research/{session_id}/message",
        json={"content": "What is AI?"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "thinking"

    # Give background task time to complete
    import time
    time.sleep(0.5)

    # Check messages in DB — should have both user and assistant
    msgs_resp = client.get(
        f"/api/research/{session_id}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    messages = msgs_resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is AI?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Claude says hello"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py::test_send_message_new -v`
Expected: FAIL

**Step 3: Rewrite `send_message` in `backend/app/api/research.py`**

```python
import asyncio
from app.services.research_runner import run_claude_message


# Track running tasks by session_id for cancellation
_running_tasks: dict[int, asyncio.Task] = {}


@router.post(
    "/research/{session_id}/message",
    response_model=SendMessageResponse,
    status_code=201,
)
async def send_message(
    session_id: int,
    body: SendMessageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    # Check if already has messages (for continuation flag)
    existing_count = len(
        db.exec(
            select(ChatMessage).where(
                ChatMessage.session_type == "research",
                ChatMessage.session_id == research.id,
            )
        ).all()
    )

    # Store user message
    message = ChatMessage(
        user_id=user.id,
        session_type="research",
        session_id=research.id,
        role="user",
        content=body.content,
    )
    db.add(message)

    # Update status to thinking
    research.status = "thinking"
    research.updated_at = datetime.utcnow()
    db.add(research)
    db.commit()
    db.refresh(message)

    # Launch background task
    task = asyncio.create_task(
        _process_claude_response(
            session_id=research.id,
            user_id=user.id,
            workspace_path=research.workspace_path,
            user_message=body.content,
            is_continuation=existing_count > 0,
        )
    )
    _running_tasks[research.id] = task

    return {
        "id": message.id,
        "content": body.content,
        "status": "thinking",
    }


async def _process_claude_response(
    session_id: int,
    user_id: int,
    workspace_path: str,
    user_message: str,
    is_continuation: bool,
) -> None:
    """Background task: run Claude CLI and store response."""
    with Session(engine) as db:
        try:
            response_text = await run_claude_message(
                workspace_path=workspace_path,
                message=user_message,
                is_continuation=is_continuation,
            )

            # Store assistant message
            assistant_msg = ChatMessage(
                user_id=user_id,
                session_type="research",
                session_id=session_id,
                role="assistant",
                content=response_text,
            )
            db.add(assistant_msg)

        except Exception as e:
            # Store error as assistant message
            error_msg = ChatMessage(
                user_id=user_id,
                session_type="research",
                session_id=session_id,
                role="assistant",
                content=f"Error: {str(e)}",
            )
            db.add(error_msg)

        finally:
            # Set status back to idle
            research = db.get(ResearchSession, session_id)
            if research:
                research.status = "idle"
                research.updated_at = datetime.utcnow()
                db.add(research)
            db.commit()
            _running_tasks.pop(session_id, None)
```

**Step 4: Run tests**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add backend/app/api/research.py backend/tests/test_research.py
git commit -m "feat: rewrite send_message with async Claude CLI execution"
```

---

### Task 6: Replace resume/stop with cancel endpoint

**Files:**
- Modify: `backend/app/api/research.py`
- Modify: `backend/tests/test_research.py`

**Step 1: Write the failing test**

```python
def test_cancel_research(
    client: TestClient,
    user_token: str,
    agent: dict,
    data_dir: Path,
    session: Session,
):
    create_resp = _create_research(client, user_token, agent["id"], name="Cancel Me")
    session_id = create_resp.json()["id"]

    # Session is idle, cancel should still succeed (no-op)
    resp = client.post(
        f"/api/research/{session_id}/cancel",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_cancel_not_found(
    client: TestClient,
    user_token: str,
):
    resp = client.post(
        "/api/research/9999/cancel",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py::test_cancel_research -v`
Expected: FAIL with 404/405

**Step 3: Add cancel endpoint, remove resume/stop endpoints**

```python
@router.post(
    "/research/{session_id}/cancel",
    response_model=ResearchSessionResponse,
)
async def cancel_research(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    # Cancel running task if exists
    task = _running_tasks.get(research.id)
    if task and not task.done():
        task.cancel()
        _running_tasks.pop(research.id, None)

    research.status = "idle"
    research.updated_at = datetime.utcnow()
    db.add(research)
    db.commit()
    db.refresh(research)
    return research
```

Delete the `resume_research_session` and `stop_research_session` endpoints.
Delete the WebSocket `research_terminal` endpoint.
Remove `tmux = TmuxManager()` and the `TmuxManager` import (research module only).

**Step 4: Remove old resume/stop tests, update related tests**

Delete: `test_resume_research_session`, `test_resume_already_running`, `test_resume_not_found`, `test_stop_research_session`, `test_stop_not_found`.

Remove resume/stop from `test_cannot_access_other_users_research`.

**Step 5: Run all tests**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add backend/app/api/research.py backend/tests/test_research.py
git commit -m "feat: replace resume/stop with cancel, remove tmux/websocket from research"
```

---

### Task 7: Update delete endpoint — remove tmux cleanup

**Files:**
- Modify: `backend/app/api/research.py`
- Modify: `backend/tests/test_research.py`

**Step 1: Update `delete_research_session`**

Remove tmux kill logic. Cancel any running task instead:

```python
@router.delete("/research/{session_id}")
async def delete_research_session(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    research = _get_session_or_404(session_id, user, db)

    # Cancel running task if exists
    task = _running_tasks.get(research.id)
    if task and not task.done():
        task.cancel()
        _running_tasks.pop(research.id, None)

    # Cleanup workspace
    workspace = Path(research.workspace_path)
    if workspace.exists():
        shutil.rmtree(workspace)

    # Delete related chat messages
    messages = db.exec(
        select(ChatMessage).where(
            ChatMessage.session_type == "research",
            ChatMessage.session_id == research.id,
        )
    ).all()
    for msg in messages:
        db.delete(msg)

    db.delete(research)
    db.commit()
    return {"detail": "Research session deleted"}
```

**Step 2: Update delete tests — remove mock_tmux dependency**

Update `test_delete_research_session`: remove `mock_tmux` from params, remove `mock_tmux.kill_session.assert_called()`.

**Step 3: Run tests**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/test_research.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add backend/app/api/research.py backend/tests/test_research.py
git commit -m "refactor: remove tmux from research delete, use task cancellation"
```

---

### Task 8: Install react-markdown and remark-gfm

**Files:**
- Modify: `frontend/package.json` (via npm install)

**Step 1: Install packages**

Run: `cd /home/tomas/projects/autocode/frontend && npm install react-markdown remark-gfm`

**Step 2: Verify installation**

Run: `cd /home/tomas/projects/autocode/frontend && node -e "require('react-markdown'); require('remark-gfm'); console.log('OK')"`

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: install react-markdown and remark-gfm"
```

---

### Task 9: Add frontend API hooks for research messages and files

**Files:**
- Modify: `frontend/src/api/research.ts`

**Step 1: Add hooks**

Add to `frontend/src/api/research.ts`:

```typescript
export interface ResearchMessage {
  id: number;
  user_id: number;
  session_type: string;
  session_id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface ResearchFile {
  name: string;
  path: string;
  size: number;
  modified_at: number;
}

export interface ResearchFileContent {
  name: string;
  path: string;
  content: string;
}

export function useResearchMessages(sessionId: number) {
  return useQuery<ResearchMessage[]>({
    queryKey: ['research-messages', sessionId],
    queryFn: () => api.get(`/research/${sessionId}/messages`).then(r => r.data),
    enabled: !!sessionId,
    refetchInterval: 2000,
  });
}

export function useResearchFiles(sessionId: number) {
  return useQuery<ResearchFile[]>({
    queryKey: ['research-files', sessionId],
    queryFn: () => api.get(`/research/${sessionId}/files`).then(r => r.data),
    enabled: !!sessionId,
    refetchInterval: 3000,
  });
}

export function useResearchFileContent(sessionId: number, path: string | null) {
  return useQuery<ResearchFileContent>({
    queryKey: ['research-file-content', sessionId, path],
    queryFn: () => api.get(`/research/${sessionId}/file-content`, { params: { path } }).then(r => r.data),
    enabled: !!sessionId && !!path,
    refetchInterval: 3000,
  });
}

export function useCancelResearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api.post(`/research/${id}/cancel`).then(r => r.data),
    onSuccess: (_, id) => qc.invalidateQueries({ queryKey: ['research-session', id] }),
  });
}
```

Also update `useSendMessage` to invalidate messages:

```typescript
export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: number; content: string }) =>
      api.post(`/research/${sessionId}/message`, { content }).then(r => r.data),
    onSuccess: (_, { sessionId }) => {
      qc.invalidateQueries({ queryKey: ['research-messages', sessionId] });
      qc.invalidateQueries({ queryKey: ['research-session', sessionId] });
    },
  });
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd /home/tomas/projects/autocode/frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/api/research.ts
git commit -m "feat: add research messages, files, and cancel API hooks"
```

---

### Task 10: Create MarkdownCanvas component

**Files:**
- Create: `frontend/src/components/MarkdownCanvas.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/MarkdownCanvas.tsx
import { useState, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useResearchFiles, useResearchFileContent, type ResearchFile } from '../api/research';

interface MarkdownCanvasProps {
  sessionId: number;
}

export default function MarkdownCanvas({ sessionId }: MarkdownCanvasProps) {
  const { data: files } = useResearchFiles(sessionId);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const { data: fileContent } = useResearchFileContent(sessionId, selectedPath);

  // Auto-select the most recently modified file
  useEffect(() => {
    if (files && files.length > 0 && !selectedPath) {
      setSelectedPath(files[0].path);
    }
  }, [files, selectedPath]);

  if (!files || files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-gray-500">
        <div className="text-center">
          <p className="text-sm">No markdown files yet.</p>
          <p className="mt-1 text-xs text-gray-600">
            Files will appear here as the research progresses.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* File tabs */}
      {files.length > 1 && (
        <div className="flex gap-1 border-b border-gray-700 px-2 py-1 overflow-x-auto">
          {files.map((f: ResearchFile) => (
            <button
              key={f.path}
              onClick={() => setSelectedPath(f.path)}
              className={`whitespace-nowrap rounded px-2 py-1 text-xs transition ${
                selectedPath === f.path
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
              }`}
            >
              {f.name}
            </button>
          ))}
        </div>
      )}

      {/* Markdown content */}
      <div className="flex-1 overflow-y-auto p-4">
        {fileContent ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <Markdown remarkPlugins={[remarkGfm]}>{fileContent.content}</Markdown>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500" />
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd /home/tomas/projects/autocode/frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/components/MarkdownCanvas.tsx
git commit -m "feat: add MarkdownCanvas component for research file rendering"
```

---

### Task 11: Rewrite ChatInterface for research

**Files:**
- Rewrite: `frontend/src/components/ChatInterface.tsx`

**Step 1: Rewrite the component**

Replace the entire ChatInterface with a new implementation that:
- Loads messages from DB via `useResearchMessages`
- Shows real assistant responses with markdown rendering
- Shows "thinking" indicator based on session status
- Replaces terminal panel with MarkdownCanvas

```tsx
// frontend/src/components/ChatInterface.tsx
import { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useResearchMessages, useResearchSession } from '../api/research';
import MarkdownCanvas from './MarkdownCanvas';

interface ChatInterfaceProps {
  sessionId: number;
  onSendMessage: (content: string) => Promise<void>;
  isSending: boolean;
}

export default function ChatInterface({ sessionId, onSendMessage, isSending }: ChatInterfaceProps) {
  const { data: messages = [] } = useResearchMessages(sessionId);
  const { data: session } = useResearchSession(sessionId);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isThinking = session?.status === 'thinking';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  async function handleSend() {
    const content = input.trim();
    if (!content || isSending || isThinking) return;
    setInput('');
    await onSendMessage(content);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] gap-4">
      {/* Chat messages - left side */}
      <div className="flex w-[60%] flex-col rounded-lg border border-gray-700 bg-gray-800">
        {/* Message list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && !isThinking && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <p className="text-gray-400">Send a message to start researching.</p>
                <p className="mt-1 text-xs text-gray-600">
                  Claude will research the topic and create markdown documents.
                </p>
              </div>
            </div>
          )}
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-200'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                <p className={`mt-1 text-xs ${msg.role === 'user' ? 'text-blue-300' : 'text-gray-500'}`}>
                  {new Date(msg.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {/* Thinking indicator */}
          {isThinking && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-gray-700 px-4 py-2 text-sm text-gray-400">
                <span className="inline-flex gap-1">
                  <span className="animate-bounce">.</span>
                  <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>.</span>
                </span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-700 p-3">
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isThinking ? 'Waiting for response...' : 'Type a message... (Shift+Enter for newline)'}
              disabled={isSending || isThinking}
              rows={1}
              className="flex-1 resize-none rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={isSending || isThinking || !input.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      </div>

      {/* Markdown Canvas - right side */}
      <div className="w-[40%] rounded-lg border border-gray-700 bg-gray-800">
        <MarkdownCanvas sessionId={sessionId} />
      </div>
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd /home/tomas/projects/autocode/frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/components/ChatInterface.tsx
git commit -m "feat: rewrite ChatInterface with DB messages and markdown canvas"
```

---

### Task 12: Update ResearchChat page — header with cancel button

**Files:**
- Modify: `frontend/src/pages/ResearchChat.tsx`

**Step 1: Update the component**

Replace resume/stop buttons with cancel button. Update status colors:

```tsx
// frontend/src/pages/ResearchChat.tsx
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useResearchSession, useSendMessage, useUpdateResearch, useCancelResearch } from '../api/research';
import ChatInterface from '../components/ChatInterface';

const statusColors: Record<string, string> = {
  idle: 'bg-gray-600',
  thinking: 'bg-blue-600 animate-pulse',
};

function EditableName({ sessionId, name }: { sessionId: number; name: string }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  const updateResearch = useUpdateResearch();

  function handleSave() {
    const trimmed = value.trim();
    if (trimmed && trimmed !== name) {
      updateResearch.mutate({ id: sessionId, name: trimmed });
    } else {
      setValue(name);
    }
    setEditing(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') { setValue(name); setEditing(false); }
  }

  if (editing) {
    return (
      <input
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className="bg-transparent text-xl font-bold text-white border-b border-blue-500 outline-none px-0 py-0"
      />
    );
  }

  return (
    <h1
      onClick={() => setEditing(true)}
      className="text-xl font-bold text-white cursor-pointer hover:text-blue-400 transition-colors"
      title="Click to rename"
    >
      {name}
    </h1>
  );
}

export default function ResearchChat() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);
  const navigate = useNavigate();
  const { data: session, isLoading, isError } = useResearchSession(sessionId);
  const sendMessage = useSendMessage();
  const cancelResearch = useCancelResearch();

  async function handleSendMessage(content: string) {
    await sendMessage.mutateAsync({ sessionId, content });
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="h-8 w-64 animate-pulse rounded bg-gray-800" />
        <div className="mt-4 h-4 w-32 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="p-6">
        <p className="text-red-400">Research session not found.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-300 transition hover:bg-gray-700"
          >
            Back
          </button>
          <div>
            <EditableName sessionId={sessionId} name={session.name} />
            <div className="mt-0.5 flex items-center gap-2">
              <span
                className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${statusColors[session.status] ?? 'bg-gray-600'}`}
              >
                {session.status}
              </span>
              <span className="text-xs text-gray-500">{session.slug}</span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          {session.status === 'thinking' && (
            <button
              onClick={() => cancelResearch.mutate(sessionId)}
              disabled={cancelResearch.isPending}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-50"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Chat Interface */}
      <ChatInterface
        sessionId={sessionId}
        onSendMessage={handleSendMessage}
        isSending={sendMessage.isPending}
      />
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd /home/tomas/projects/autocode/frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/pages/ResearchChat.tsx
git commit -m "feat: update ResearchChat header with cancel button and new statuses"
```

---

### Task 13: Add Tailwind typography plugin for prose styles

**Files:**
- Modify: `frontend/package.json` (via npm install)
- Modify: `frontend/src/index.css` (or tailwind config)

**Step 1: Install typography plugin**

Run: `cd /home/tomas/projects/autocode/frontend && npm install @tailwindcss/typography`

**Step 2: Add to Tailwind CSS import**

Check `frontend/src/index.css` for existing Tailwind imports and add typography plugin. If using Tailwind v4 with CSS-based config, add:

```css
@plugin "@tailwindcss/typography";
```

**Step 3: Verify build works**

Run: `cd /home/tomas/projects/autocode/frontend && npm run build`

**Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/index.css
git commit -m "chore: install @tailwindcss/typography for prose styles"
```

---

### Task 14: Remove unused useResearchAction hook

**Files:**
- Modify: `frontend/src/api/research.ts`

**Step 1: Remove `useResearchAction` export**

The `useResearchAction` hook (for resume/stop) is no longer used. Remove it from `research.ts`.

**Step 2: Verify no other files import it**

Run: `cd /home/tomas/projects/autocode && grep -r "useResearchAction" frontend/src/`
Expected: No results

**Step 3: Verify TypeScript compiles**

Run: `cd /home/tomas/projects/autocode/frontend && npx tsc --noEmit`

**Step 4: Commit**

```bash
git add frontend/src/api/research.ts
git commit -m "chore: remove unused useResearchAction hook"
```

---

### Task 15: Run full test suite and build

**Step 1: Run backend tests**

Run: `cd /home/tomas/projects/autocode && python -m pytest backend/tests/ -v`
Expected: All tests pass

**Step 2: Run frontend build**

Run: `cd /home/tomas/projects/autocode/frontend && npm run build`
Expected: Build succeeds

**Step 3: Fix any issues found**

Address any test failures or build errors.

**Step 4: Final commit if needed**

```bash
git add -A
git commit -m "fix: address test and build issues from research redesign"
```

---

### Task 16: Deploy and verify

**Step 1: Push changes**

Run: `cd /home/tomas/projects/autocode && git push`

**Step 2: Restart backend on server**

SSH to VPS and restart the autocode service.

**Step 3: Verify on production**

- Navigate to a research session
- Send a message — verify it appears in chat
- Wait for Claude response — verify it appears as assistant message
- Check that .md files appear in the canvas panel
- Refresh page — verify messages persist
