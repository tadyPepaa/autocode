# Research Agent Redesign

## Problem

The current Research Agent has three key issues:

1. **Chat messages are local state only** — lost on page refresh, no DB persistence
2. **Assistant responses are placeholders** — "Message sent. See terminal for Claude Code output." instead of actual Claude responses
3. **Terminal preview is raw tmux output** — not user-friendly, doesn't show research results

## Design

### Architecture Change: One-shot Claude CLI

Replace interactive tmux-based Claude Code with one-shot CLI mode using `claude -p`:

- **First message**: `claude -p "message" --dangerously-skip-permissions --output-format json`
- **Subsequent messages**: `claude -p "message" --dangerously-skip-permissions --output-format json -c`

The `-c` flag continues the most recent conversation in the workspace directory, maintaining full context. Claude Code indexes conversations by project path, so each research session (with its own workspace) has isolated conversation history.

### Backend Changes

#### Modified: `POST /research/{id}/message`

1. Store user message as ChatMessage in DB (already done)
2. Run Claude in asyncio background task via `asyncio.create_subprocess_exec`
3. Parse JSON output, extract response text
4. Store assistant response as ChatMessage in DB
5. Update session status: `idle` → `thinking` → `idle`

#### New: `GET /research/{id}/messages`

Return all ChatMessages for the research session, ordered by created_at. Same pattern as learning module's `GET /courses/{id}/messages`.

#### New: `GET /research/{id}/files`

List `.md` files in the research workspace directory. Return filename, path, size, and last modified timestamp.

#### New: `GET /research/{id}/file-content`

Read and return the content of a specific file from the workspace. Takes a `path` query parameter (relative to workspace root). Validates path is within workspace to prevent directory traversal.

#### Modified: `POST /agents/{agent_id}/research` (create)

- Don't create tmux session
- Write agent identity to `CLAUDE.md` in workspace directory
- Set initial status to `idle`

#### Removed

- tmux session creation/management for research
- WebSocket terminal streaming endpoint
- Resume/Stop endpoints → replaced with Cancel (kills running subprocess)

#### New: `POST /research/{id}/cancel`

Kill the running Claude subprocess if session is in `thinking` state.

### Frontend Changes

#### Chat Panel (left 60%)

- Load messages from DB via `useResearchMessages(sessionId)` hook with `refetchInterval: 2000`
- Display user messages (blue, right-aligned) and assistant messages (gray, left-aligned)
- Render assistant messages with markdown (react-markdown)
- Show animated "thinking" indicator while status is `thinking`
- Messages persist across page refreshes

#### Canvas Panel (right 40%)

Replace xterm.js terminal with markdown file viewer:

- Poll `GET /research/{id}/files` for `.md` files in workspace
- Auto-select the most recently modified `.md` file
- Render with `react-markdown` + `remark-gfm` for GitHub-flavored markdown
- File selector tabs when multiple `.md` files exist
- Auto-refresh content every 3 seconds during active research

#### Header Changes

- Remove Resume/Stop buttons
- Add Cancel button (visible only during `thinking` state)
- Status badge: `idle` (gray) / `thinking` (blue animated)

### Removed Dependencies (for research)

- `@xterm/xterm` and `@xterm/addon-fit` (still used by coding agent)
- WebSocket terminal connection
- tmux session management

### Status Model

| Old | New | Meaning |
|---|---|---|
| `active` | `thinking` | Claude is processing a message |
| `stopped` | `idle` | Ready for new messages |

### Data Flow

```
User types message
  → POST /research/{id}/message
  → Store user ChatMessage in DB
  → Start asyncio background task:
      → Run: claude -p "msg" --dangerously-skip-permissions --output-format json [-c]
      → cwd = workspace_path
      → Wait for completion
      → Parse JSON response
      → Store assistant ChatMessage in DB
      → Set status = idle
  → Return immediately with status "thinking"

Frontend polls GET /research/{id}/messages every 2s
  → Displays new messages as they appear
  → Shows "thinking" indicator while status = thinking

Canvas polls GET /research/{id}/files every 3s
  → Renders selected .md file with react-markdown
```
