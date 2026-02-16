# Research: Autonomous AI Software Development - PM Agent Orchestrating Coding Agents

**Date:** 2026-02-16
**Goal:** Comprehensive analysis of existing approaches and tools for building a PM-level AI agent that directs coding agents (specifically Claude Code).

---

## Table of Contents

1. [Claude Agent SDK (formerly Claude Code SDK)](#1-claude-agent-sdk)
2. [Claude Code CLI Automation](#2-claude-code-cli-automation)
3. [Claude Code Native Multi-Agent Capabilities](#3-claude-code-native-multi-agent)
4. [Existing Orchestrator / PM Agent Frameworks](#4-existing-frameworks)
5. [Architecture Patterns for Multi-Agent Development](#5-architecture-patterns)
6. [Anthropic Computer Use & Tool Use](#6-anthropic-computer-use)
7. [Comparative Analysis & Recommendations](#7-comparative-analysis)

---

## 1. Claude Agent SDK (formerly Claude Code SDK) {#1-claude-agent-sdk}

### History & Naming

- **May 2025:** Launched as "Claude Code SDK" alongside Claude Opus 4 and Sonnet 4
- **September 2025:** Renamed to "Claude Agent SDK" alongside Claude Sonnet 4.5
- **February 2026:** Current versions: Python v0.1.34, TypeScript v0.2.37 (1.85M+ weekly npm downloads)

### Core Architecture

The Agent SDK exposes the same battle-tested infrastructure powering Claude Code as a programmable library. Key difference from the Anthropic Client SDK: **the Agent SDK handles the entire tool loop autonomously** -- you don't implement tool execution yourself.

```python
# Client SDK: You implement the tool loop
response = client.messages.create(...)
while response.stop_reason == "tool_use":
    result = your_tool_executor(response.tool_use)
    response = client.messages.create(tool_result=result, **params)

# Agent SDK: Claude handles tools autonomously
async for message in query(prompt="Fix the bug in auth.py"):
    print(message)
```

### Core API: `query()` Function

Both Python and TypeScript expose `query()` as the primary interface:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Find and fix the bug in auth.py",
    options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"]),
):
    print(message)
```

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Find and fix the bug in auth.py",
  options: { allowedTools: ["Read", "Edit", "Bash"] }
})) {
  console.log(message);
}
```

### Built-in Tools

| Tool | Description |
|------|-------------|
| **Read** | Read any file in working directory |
| **Write** | Create new files |
| **Edit** | Make precise edits to existing files |
| **Bash** | Run terminal commands, scripts, git |
| **Glob** | Find files by pattern |
| **Grep** | Search file contents with regex |
| **WebSearch** | Search the web |
| **WebFetch** | Fetch and parse web pages |
| **AskUserQuestion** | Ask user clarifying questions |
| **Task** | Spawn subagents |

### Subagent Orchestration (Key for PM Agent)

The SDK supports defining custom subagents with specialized roles:

```python
async for message in query(
    prompt="Use the code-reviewer agent to review this codebase",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Task"],
        agents={
            "code-reviewer": AgentDefinition(
                description="Expert code reviewer for quality and security reviews.",
                prompt="Analyze code quality and suggest improvements.",
                tools=["Read", "Glob", "Grep"],
            )
        },
    ),
):
    ...
```

Messages from subagents include `parent_tool_use_id` for tracking.

### Permissions System

Three layers of control:
1. **Permission modes:** `manual` (default), `acceptEdits`, `acceptAll`, `bypassPermissions`
2. **Permission rules:** `deny` -> `allow` -> `ask` evaluation order
3. **`canUseTool` callback:** Runtime tool approval at the application level
4. **Sandboxing:** OS-level filesystem and network isolation for Bash commands

### Session Management

Sessions can be captured and resumed, enabling multi-turn workflows:

```python
# Capture session ID
async for message in query(prompt="Read the auth module", ...):
    if hasattr(message, "subtype") and message.subtype == "init":
        session_id = message.session_id

# Resume later with full context
async for message in query(
    prompt="Now find all places that call it",
    options=ClaudeAgentOptions(resume=session_id),
):
    ...
```

### Hooks (Lifecycle Callbacks)

SDK hooks run custom code at key points: `PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`. These can validate, log, block, or transform agent behavior.

### MCP Integration

Connect to external systems (databases, browsers, APIs) via Model Context Protocol:

```python
options=ClaudeAgentOptions(
    mcp_servers={
        "playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]}
    }
)
```

### Plugins

Extend agents with custom commands, agents, skills, hooks, and MCP servers. Plugin ecosystem is in public beta (October 2025+), with 1,537+ skills deployed.

### Authentication

- Anthropic API key (default)
- Amazon Bedrock (`CLAUDE_CODE_USE_BEDROCK=1`)
- Google Vertex AI (`CLAUDE_CODE_USE_VERTEX=1`)
- Microsoft Azure AI Foundry (`CLAUDE_CODE_USE_FOUNDRY=1`)

### Assessment

| Aspect | Rating |
|--------|--------|
| **Maturity** | Production-grade, 1.85M+ weekly downloads |
| **Claude Code Integration** | Native -- it IS Claude Code's engine |
| **Autonomous Operation** | Full support with `bypassPermissions` + sandboxing |
| **Strengths** | Same runtime as Claude Code, built-in tools, subagent orchestration, session persistence, MCP extensibility |
| **Weaknesses** | Locked to Anthropic models, no built-in multi-model orchestration, cost can escalate with parallel agents |

---

## 2. Claude Code CLI Automation {#2-claude-code-cli-automation}

### Print Mode (`-p` / `--print`)

Non-interactive execution for scripts and CI/CD:

```bash
claude -p "Find and fix the bug in auth.py" --allowedTools "Read,Edit,Bash"
```

### Output Formats

| Format | Flag | Description |
|--------|------|-------------|
| Text | `--output-format text` | Default, human-readable |
| JSON | `--output-format json` | Structured with session ID, cost metadata |
| Stream-JSON | `--output-format stream-json` | NDJSON, real-time streaming |

### Structured Output with JSON Schema

```bash
claude -p "Extract function names from auth.py" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}}}'
```

### Session Continuation

```bash
# First request
claude -p "Review this codebase for performance issues"

# Continue most recent conversation
claude -p "Now focus on the database queries" --continue

# Resume specific session
session_id=$(claude -p "Start a review" --output-format json | jq -r '.session_id')
claude -p "Continue that review" --resume "$session_id"
```

### System Prompt Customization

```bash
# Append to default system prompt
gh pr diff "$1" | claude -p \
  --append-system-prompt "You are a security engineer. Review for vulnerabilities." \
  --output-format json

# Fully replace system prompt
claude -p "..." --system-prompt "Custom system prompt here"
```

### Tool Auto-Approval with Prefix Matching

```bash
claude -p "Create a commit" \
  --allowedTools "Bash(git diff *),Bash(git log *),Bash(git status *),Bash(git commit *)"
```

Note: The space before `*` is important -- `Bash(git diff *)` allows any command starting with `git diff `, while `Bash(git diff*)` would also match `git diff-index`.

### Hooks System (File-Based)

Configured in `~/.claude/settings.json` (global) or `.claude/settings.json` (project):

**Available hook events:**
- `PreToolUse` -- before a tool runs (can block/modify)
- `PostToolUse` -- after a tool completes
- `Notification` -- when Claude sends an alert
- `Stop` -- when the agent finishes
- `UserPromptSubmit` -- when user sends a prompt
- `SessionStart` -- at session start
- `SubagentStart` / `SubagentStop` -- subagent lifecycle

**New in January 2026:** Async hooks (`"async": true`) run in background without blocking execution.

**Input modification (v2.0.10+):** `PreToolUse` hooks can modify tool inputs before execution for transparent sandboxing, security enforcement, convention adherence, etc.

### Assessment

| Aspect | Rating |
|--------|--------|
| **Maturity** | Stable, well-documented |
| **Automation Quality** | Excellent for CI/CD, scripting, pipelines |
| **Strengths** | Simple to use, JSON streaming, session management, tool control |
| **Weaknesses** | Subprocess-based (IPC overhead vs SDK), no native callback hooks (shell commands only) |

---

## 3. Claude Code Native Multi-Agent Capabilities {#3-claude-code-native-multi-agent}

### Subagents (Single Session)

Each subagent runs in its own context window with custom system prompt, specific tool access, and independent permissions. **Parallelism capped at 10** concurrent subagents (additional queued).

**Built-in subagents:**
- **Explore** -- fast, read-only (Haiku model), for codebase search
- **Plan** -- research agent for plan mode
- **General-purpose** -- all tools, complex multi-step tasks

**Custom subagent definition** (Markdown files with YAML frontmatter):

```markdown
---
name: code-reviewer
description: Expert code review specialist. Use proactively after code changes.
tools: Read, Grep, Glob, Bash
model: sonnet
permissionMode: dontAsk
memory: user
---
You are a senior code reviewer...
```

**Key features:**
- Model selection per subagent: `sonnet`, `opus`, `haiku`, `inherit`
- Permission modes: `default`, `acceptEdits`, `dontAsk`, `delegate`, `bypassPermissions`, `plan`
- Persistent memory across sessions (`user`, `project`, `local` scope)
- Skill preloading for domain knowledge
- Lifecycle hooks scoped to subagent
- Background execution with Ctrl+B
- Can be defined via CLI `--agents` JSON flag

**Scoping:**
| Location | Scope | Priority |
|----------|-------|----------|
| `--agents` CLI flag | Current session | 1 (highest) |
| `.claude/agents/` | Current project | 2 |
| `~/.claude/agents/` | All projects | 3 |
| Plugin `agents/` | Where plugin enabled | 4 (lowest) |

### Agent Teams (Multi-Session) -- NEW February 2026

**Experimental feature** shipped alongside Opus 4.6. Requires feature flag: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.

Key differences from subagents:
- **Subagents:** Run within a single session, report only to parent
- **Agent Teams:** Multiple independent sessions with shared task list, direct messaging between teammates, team lead orchestration

**Architecture:**
- One session acts as **team lead** (coordinating, assigning tasks, synthesizing)
- **Teammates** work independently in their own context windows
- Shared task list with DAG dependency support
- Direct messaging between teammates (not just lead)
- Can interact with individual teammates directly

**Use cases:**
- Parallel research/review of different aspects
- New features with separate pieces per teammate
- Debugging with competing hypotheses
- Cross-layer coordination (frontend, backend, tests)

**Cost considerations:** A 3-teammate team running 30 minutes uses roughly 3-4x tokens of a single sequential session.

### Task Tool (DAG-Based Dependencies)

Tasks support directed acyclic graphs (DAGs):
- Task 3 (Run Tests) blocks on Task 1 (Build API) and Task 2 (Configure Auth)
- Tasks persist across context compactions
- Task state survives memory resets in long sessions

### Assessment

| Aspect | Rating |
|--------|--------|
| **Maturity** | Subagents: stable; Agent Teams: experimental (Feb 2026) |
| **PM Agent Fit** | Excellent -- native hierarchical orchestration |
| **Strengths** | Native to Claude Code, shared context, DAG dependencies, persistent memory, team coordination |
| **Weaknesses** | Agent Teams still experimental, locked to Claude models, token cost scales linearly with team size |

---

## 4. Existing Orchestrator / PM Agent Frameworks {#4-existing-frameworks}

### 4.1 LangGraph (LangChain)

**Status:** LangChain has officially shifted focus: "Use LangGraph for agents, not LangChain." LangGraph is now the primary agent framework.

**Architecture:** Graph-based workflow with nodes (agent steps) and edges (transitions). Supports cycles, parallel branches, and complex state management.

**Strengths:**
- Most flexible architecture -- any workflow topology
- Excellent state management
- Strong community (80K+ GitHub stars for LangChain ecosystem)
- Model-agnostic
- LangSmith for observability

**Weaknesses:**
- Steep learning curve
- Verbose for simple workflows
- Requires implementing tool execution yourself
- No built-in file/code tools

**Claude Code Integration:** Would need to wrap Claude Agent SDK calls as LangGraph nodes. Possible but adds abstraction overhead.

**Verdict:** Good for building a custom PM orchestrator from scratch if you need complex, non-linear workflows. Overkill if Claude Code's native features suffice.

### 4.2 CrewAI

**Status:** Production-ready, popular for role-based multi-agent systems.

**Architecture:** Role-based model inspired by organizational structures. Agents have roles, goals, and backstories. Tasks are assigned based on agent specializations.

**Strengths:**
- Intuitive role-based design (close to PM/developer mental model)
- Easy to set up and understand
- Good for sequential and parallel task execution
- Model-agnostic

**Weaknesses:**
- Less flexible than LangGraph for complex workflows
- Limited state management between tasks
- Roles can feel constraining for dynamic workloads

**Claude Code Integration:** Could define a CrewAI agent that invokes Claude Code SDK as its execution engine. Natural fit for PM -> developer hierarchy.

**Verdict:** Good conceptual fit for PM-agent pattern, but adds unnecessary abstraction if Claude Code's native subagents + agent teams cover the use case.

### 4.3 Microsoft AutoGen / Semantic Kernel

**Status:** In October 2025, Microsoft merged AutoGen with Semantic Kernel into a unified "Microsoft Agent Framework." GA planned for Q1 2026 with production SLAs, multi-language support, and Azure integration.

**Architecture:** Conversation-based -- workflows are conversations between agents. Support for group chat, nested conversations, and code execution.

**Strengths:**
- Enterprise-grade with Microsoft backing
- Strong Azure integration
- Multi-language support
- Unified framework post-merge

**Weaknesses:**
- Heavy Microsoft/Azure ecosystem dependency
- Conversation model can be limiting for complex orchestration
- Still in transition (merger not yet GA)

**Claude Code Integration:** Would need custom agent implementation wrapping Claude Code. More suitable for Azure-centric enterprises.

**Verdict:** Best for Microsoft/Azure shops. Unnecessary complexity for Claude-centric setups.

### 4.4 OpenAI Swarm

**Status:** Experimental, explicitly not production-ready (OpenAI's own statement).

**Architecture:** Lightweight routine-based model. Agents defined through prompts and function docstrings. LLM infers behavior through docstrings.

**Strengths:**
- Extremely simple to understand
- Good for learning multi-agent concepts
- Fast prototyping

**Weaknesses:**
- **Not production-ready** (OpenAI's words)
- No formal orchestration or state model
- Flexible but imprecise routing
- OpenAI-only

**Claude Code Integration:** Not relevant -- OpenAI-only, experimental.

**Verdict:** Skip for production use. Educational value only.

### 4.5 MetaGPT

**Status:** Research-oriented multi-agent framework simulating a software company.

**Architecture:** SOP-based (Standard Operating Procedures). Agents have roles (ProductManager, Architect, Engineer, QAEngineer) and follow structured procedures. Mimics waterfall software development.

**Strengths:**
- Structured software development process
- Generates PRD, architecture, code, tests in sequence
- Research-backed (GPT-series models)

**Weaknesses:**
- Rigid, waterfall-like workflow
- Better for greenfield projects than incremental work
- Heavy setup
- Research-grade, not production-grade
- Primarily GPT-oriented

**Claude Code Integration:** Could theoretically use Claude as backend LLM, but the SOP structure conflicts with Claude Code's more flexible approach.

**Verdict:** Interesting for automated project generation. Poor fit for ongoing development PM agent.

### 4.6 ChatDev

**Status:** Research demo of a "virtual software company."

**Architecture:** Chat-chain approach where agents in different roles (CEO, CTO, Programmer, Tester) communicate through structured conversations across design, coding, and testing phases.

**Strengths:**
- Novel puppet-style multi-agent collaboration (May 2025 update)
- Outperformed MetaGPT in quality metrics
- Academic rigor

**Weaknesses:**
- Research demo, not production tool
- Fixed role structure
- Better for generating new software than maintaining existing

**Claude Code Integration:** Minimal. Different paradigm.

**Verdict:** Academic interest only for production PM agent use case.

### 4.7 OpenHands (formerly OpenDevin)

**Status:** Leading open-source autonomous coding agent platform. Active development.

**Architecture:** Model-agnostic platform for cloud coding agents. Runs in sandboxed Docker containers. Supports multiple LLM backends.

**Benchmark results:**
- Claude Opus: Top performer on SWE-Bench Issue Resolution, frontend development, unit test writing
- 43.20% on SWE-bench Verified with Claude 3.7 Sonnet
- 19.25% highest on SWE-bench Live (more realistic)
- Introduced OpenHands Index (January 2026) as broader benchmark

**Strengths:**
- Model-agnostic
- Strong sandboxing (Docker-based)
- Excellent benchmark results
- Community-driven
- Good for autonomous task execution

**Weaknesses:**
- Single-agent architecture (no native multi-agent orchestration)
- Docker dependency
- Not designed as PM-level orchestrator

**Claude Code Integration:** Potential to use as a worker agent, but competes rather than complements Claude Code.

**Verdict:** Alternative to Claude Code for isolated task execution. Not suitable as PM orchestrator.

### 4.8 SWE-agent (Princeton)

**Status:** Research tool for autonomous software engineering.

**Architecture:** Custom agent-computer interface (ACI) for LLMs to interact with codebases. Focused on issue resolution.

**Strengths:**
- Strong academic backing (Princeton NLP)
- Good SWE-bench results
- Clean ACI design

**Weaknesses:**
- Research-focused
- Single-agent
- No orchestration capabilities

**Claude Code Integration:** Not relevant. Competing approach.

**Verdict:** Research tool, not applicable for PM orchestration.

### 4.9 Aider

**Status:** Mature terminal-based AI pair programming tool.

**Architecture:** Single-agent, file-focused. User gives files, Aider modifies them via conversation. Supports many LLM backends.

**Strengths:**
- Excellent for focused code editing
- Model-agnostic (works with Claude, GPT, DeepSeek, local models)
- Mature and reliable
- Good git integration

**Weaknesses:**
- Not designed for orchestration
- Single-agent, single-task
- No PM/delegation capabilities

**Claude Code Integration:** Could be used as alternative coding backend, but no orchestration synergy.

**Verdict:** Good coding tool, not an orchestration framework.

### 4.10 Cline / Roo Code

**Status:** Leading open-source VS Code extension for autonomous coding. Human-in-the-loop by design.

**Architecture:** IDE-integrated agent with file editing, terminal commands, browser automation, MCP tool integration. Human approves each action.

**Strengths:**
- Model-agnostic (OpenAI, Anthropic, Google, local)
- Strong human-in-the-loop controls
- MCP integration
- VS Code integration
- Active community (top open-source coding agent in 2025)

**Weaknesses:**
- IDE-dependent (VS Code)
- Human approval required for each step (by design)
- No multi-agent orchestration
- Not headless-friendly

**Claude Code Integration:** Competes with Claude Code. Different paradigm (IDE vs terminal).

**Verdict:** Not suitable for autonomous PM orchestration. Different design philosophy.

### 4.11 claude-flow (ruvnet)

**Status:** Community-driven orchestration platform specifically for Claude. Claims to be "#1 in agent-based frameworks."

**Architecture:** MCP-based orchestration of Claude Code instances. 175+ MCP tools, 64-agent system, swarm intelligence, RAG integration.

**Key features:**
- Claude-flow as "brain" (planning/coordinating), Claude Code as "hands" (execution)
- Self-learning neural capabilities (v3)
- Learns from task execution patterns
- Intelligent work routing

**Strengths:**
- Built specifically for Claude Code orchestration
- MCP protocol native
- Self-learning capabilities

**Weaknesses:**
- Community project, uncertain long-term support
- Marketing claims may exceed reality
- Complex setup
- Limited production validation

**Claude Code Integration:** Native -- designed for it.

**Verdict:** Worth evaluating as inspiration. Most directly relevant community project, but assess actual quality vs marketing carefully.

### 4.12 Google ADK (Agent Development Kit)

**Status:** Production framework from Google. Supports A2A (Agent2Agent) protocol for cross-framework agent communication.

**Architecture:** Modular, model-agnostic framework. RemoteA2aAgent for cross-ecosystem communication. Hierarchical multi-agent support.

**A2A Protocol (v0.2):**
- Open communication standard for agents across frameworks
- Works with ADK, LangGraph, CrewAI, or others
- Stateless interaction support
- Standardized authentication (OpenAPI-like)

**Strengths:**
- Google backing, strong documentation
- A2A protocol for cross-framework communication
- Multi-language (Python, Go)
- Model-agnostic

**Weaknesses:**
- Optimized for Gemini ecosystem
- Less mature than LangGraph
- A2A adoption still early

**Claude Code Integration:** Could use A2A protocol for inter-agent communication. Not directly useful as orchestrator for Claude Code.

**Verdict:** Interesting for A2A protocol standardization. Not primary choice for Claude-centric orchestration.

### 4.13 Devin (Cognition)

**Status:** First commercial "fully autonomous AI software engineer." Mixed real-world results.

**Architecture:** End-to-end autonomous agent with its own IDE, browser, and terminal. Cloud-hosted sandbox.

**Strengths:**
- Fully autonomous end-to-end
- Own development environment
- Good at self-contained tasks

**Weaknesses:**
- Independent evaluations showed only 3/20 tasks completed successfully
- Not open-source
- Expensive (usage-based beyond $20/month Core)
- Black box -- limited customization

**Claude Code Integration:** None. Competing closed product.

**Verdict:** Market proof-of-concept for autonomous coding. Not usable as building block.

---

## 5. Architecture Patterns for Multi-Agent Development {#5-architecture-patterns}

### 5.1 Hierarchical (PM Agent -> Coding Agents)

The most relevant pattern for this project.

**Structure:**
- Top-level PM agent: handles goal decomposition, task assignment, progress tracking
- Mid-level specialist agents: domain experts (frontend, backend, testing, review)
- Worker agents: execute specific coding tasks

**Proven pattern (from production deployments):**
- **Planners** continuously explore the codebase and create tasks
- **Workers** execute assigned tasks independently, push changes when done
- **Judge agents** determine whether to continue at each cycle end

**Implementation with Claude Code:**
1. PM agent uses Claude Agent SDK with `permissionMode: "delegate"`
2. Spawns subagents/teammates for specific domains
3. Uses DAG-based task dependencies
4. Judge/review subagent validates output

### 5.2 Plan-Execute-Review Loop

**The industry-proven cycle:**
1. **Plan:** PM agent analyzes requirements, decomposes into tasks, creates DAG
2. **Execute:** Worker agents implement tasks in parallel where possible
3. **Review:** Critic/judge agent evaluates output against criteria
4. **Iterate:** If review fails, refine plan and re-execute

**Generator-Critic variant:**
- Generator agent produces code/solutions
- Critic agent reviews against hard-coded criteria
- Refiner agent iteratively improves based on critique

### 5.3 Peer-to-Peer Agent Collaboration

**Claude Code Agent Teams implement this:**
- Teammates share findings and challenge each other
- Direct messaging between peers (not just through lead)
- Best for: research, debugging with competing hypotheses, cross-layer work

### 5.4 Human-in-the-Loop Patterns

**Levels of autonomy (from Claude Code's permission system):**

| Level | Claude Code Mode | Description |
|-------|-----------------|-------------|
| Full human control | `manual` | Approve every action |
| Supervised autonomy | `acceptEdits` | Auto-approve edits, approve commands |
| Gated autonomy | `dontAsk` + `allowedTools` | Auto-approve specific tool categories |
| Full autonomy | `bypassPermissions` + sandbox | Everything allowed within sandbox |

**Recommended for PM agent:** Gated autonomy with `bypassPermissions` inside strong sandboxing. Human reviews at plan/review gates, not individual tool calls.

### 5.5 Git-Based Memory and Coordination

**Industry pattern for coherent output at scale:**
- Use git branches as unit of work isolation
- Each agent/teammate works on its own branch
- PM agent handles merge coordination
- Git history serves as persistent memory
- PR-based review gates

### 5.6 Context Engineering

**Critical for multi-agent quality:**
- CLAUDE.md files for project-wide context
- Skills preloaded into subagents for domain knowledge
- Persistent memory (`user`, `project`, `local` scope) for cross-session learning
- Explicit task instructions with file references and success criteria
- DAG dependencies ensure proper ordering

---

## 6. Anthropic Computer Use & Tool Use {#6-anthropic-computer-use}

### Computer Use

- Introduced late 2024 for Claude 3.5 Sonnet as experimental beta
- Evolved into "gold standard for agentic AI" by early 2026
- Claude can navigate desktops, manipulate software, execute multi-step workflows
- OSWorld benchmark: from single-digit to 60%+ performance (Claude 4.5 era)
- **Cowork** (January 2026): consumer macOS app repackaging computer use for non-coders

### Advanced Tool Use (2025-2026)

1. **Programmatic Tool Calling:** Claude writes code that calls multiple tools, processes outputs, and controls what enters its context window. Reduces API round-trips.

2. **Tool Search Tool:** Claude searches thousands of tools without consuming context window. Enables massive tool libraries.

### Relevance for PM Agent

Computer use is relevant if the PM agent needs to interact with external tools (Jira, Figma, browsers) that don't have MCP servers. For code-focused work, the Agent SDK's built-in tools are more efficient and reliable.

---

## 7. Comparative Analysis & Recommendations {#7-comparative-analysis}

### Best Approach for PM Agent -> Claude Code Architecture

Given the research, the **most practical approach** is to build on Claude Code's native capabilities:

#### Tier 1: Native Claude Code (Recommended Starting Point)

| Component | Implementation |
|-----------|---------------|
| **PM Agent** | Custom subagent or `--agent` main thread with `delegate` permission mode |
| **Worker Agents** | Claude Code subagents or Agent Team teammates |
| **Orchestration** | DAG-based Task system with dependencies |
| **Execution** | Claude Agent SDK (Python or TypeScript) |
| **Context** | CLAUDE.md + skills + persistent memory |
| **Review** | Dedicated critic subagent + hooks for validation |

**Why:** Zero integration overhead, native multi-agent support (subagents + agent teams), built-in tools, session management, sandboxing. Everything needed is already in the ecosystem.

#### Tier 2: Claude Agent SDK + LangGraph (For Complex Orchestration)

If native Claude Code orchestration proves insufficient (e.g., need complex non-linear workflows, human approval at specific gates, integration with external systems):

| Component | Implementation |
|-----------|---------------|
| **PM Agent** | LangGraph graph with PM logic as nodes |
| **Worker Agents** | Claude Agent SDK `query()` calls as LangGraph tool nodes |
| **Orchestration** | LangGraph state machine with conditional edges |
| **Review Gates** | LangGraph decision nodes |
| **Observability** | LangSmith |

**Why:** LangGraph provides the most flexible orchestration topology while Claude Agent SDK handles the actual coding work.

#### Tier 3: CrewAI Wrapper (For Simple Role-Based Setup)

If the PM-developer relationship is straightforward and doesn't need complex state:

| Component | Implementation |
|-----------|---------------|
| **PM Agent** | CrewAI agent with PM role/goal |
| **Worker Agents** | CrewAI agents using Claude Agent SDK as tools |
| **Orchestration** | CrewAI task flow |

**Why:** Intuitive role-based setup. Lower ceiling but faster to prototype.

### Decision Matrix

| Criterion | Native Claude | SDK + LangGraph | SDK + CrewAI | claude-flow | OpenHands |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Integration effort | **Low** | Medium | Medium | Medium | High |
| Flexibility | Medium | **High** | Low | Medium | Low |
| Autonomous operation | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| Multi-model support | No | **Yes** | **Yes** | No | **Yes** |
| Production readiness | **High** | **High** | High | Low | Medium |
| Maintenance burden | **Low** | Medium | Medium | High | High |
| Community/docs | **Excellent** | **Excellent** | Good | Low | Good |
| Cost efficiency | **Best** | Good | Good | Unknown | Good |

### Key Industry Insights (2025-2026)

1. **Gartner:** Multi-agent system inquiries surged 1,445% from Q1 2024 to Q2 2025. By end 2026, 40% of enterprise apps will include task-specific AI agents (up from <5% in 2025).

2. **DORA Report (Google 2025):** 90% AI adoption increase correlates with 9% more bugs, 91% more code review time, 154% larger PRs. **Human oversight remains critical.**

3. **Industry consensus:** "Coherence through orchestration, not autonomy" -- the path to scale runs through hierarchical agent architectures, git-based memory, context engineering, and rigorous verification loops.

4. **Token economics:** A 3-agent team uses ~3-4x tokens of a single session. For a 16-agent team across 2,000 sessions (real production case): ~2 billion input tokens, under $20,000.

5. **Microsoft convergence:** AutoGen + Semantic Kernel -> unified Microsoft Agent Framework (GA Q1 2026). Signals industry consolidation.

6. **Google A2A:** Agent2Agent protocol as emerging standard for cross-framework agent communication. Worth monitoring for future interoperability.

### Concrete Recommendation for This Project

**Start with Tier 1 (Native Claude Code):**

1. Build PM agent as a custom Claude Code subagent with `delegate` permission mode
2. Define specialist subagents (planner, coder, reviewer, tester) as `.claude/agents/*.md` files
3. Use the Claude Agent SDK (TypeScript) for programmatic orchestration
4. Implement plan-execute-review loop using DAG-based tasks
5. Use persistent memory for cross-session learning
6. Enable Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) for parallel work

**Only escalate to Tier 2 (LangGraph)** if you encounter:
- Need for complex conditional routing between agents
- Integration with non-Claude systems
- Custom state management beyond what sessions provide
- Need for LangSmith-level observability

---

## Sources

### Official Documentation
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Run Claude Code Programmatically](https://code.claude.com/docs/en/headless)
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)
- [Agent Teams](https://code.claude.com/docs/en/agent-teams)
- [Claude Code Hooks](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code Sandboxing](https://code.claude.com/docs/en/sandboxing)
- [Agent SDK Permissions](https://platform.claude.com/docs/en/agent-sdk/permissions)
- [Agent SDK Secure Deployment](https://platform.claude.com/docs/en/agent-sdk/secure-deployment)
- [Claude Code Plugins](https://code.claude.com/docs/en/plugins)
- [Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python)
- [Agent SDK TypeScript Reference](https://platform.claude.com/docs/en/agent-sdk/typescript)

### Framework Comparisons
- [A Detailed Comparison of Top 6 AI Agent Frameworks in 2026](https://www.turing.com/resources/ai-agent-frameworks)
- [LangGraph vs CrewAI vs AutoGen: Top 10 AI Agent Frameworks](https://o-mega.ai/articles/langgraph-vs-crewai-vs-autogen-top-10-agent-frameworks-2026)
- [CrewAI vs LangGraph vs AutoGen (DataCamp)](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [The AI Agent Framework Landscape in 2025](https://medium.com/@hieutrantrung.it/the-ai-agent-framework-landscape-in-2025-what-changed-and-what-matters-3cd9b07ef2c3)

### Multi-Agent Architecture
- [AI Coding Agents in 2026: Coherence Through Orchestration](https://mikemason.ca/writing/ai-coding-agents-jan-2026/)
- [Google's Eight Essential Multi-Agent Design Patterns (InfoQ)](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/)
- [Designing Effective Multi-Agent Architectures (O'Reilly)](https://www.oreilly.com/radar/designing-effective-multi-agent-architectures/)
- [Developer's Guide to Multi-Agent Patterns in ADK (Google)](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- [Agentic AI Design Patterns (Medium)](https://medium.com/@balarampanda.ai/agentic-ai-design-patterns-choosing-the-right-multimodal-multi-agent-architecture-2022-2025-046a37eb6dbe)

### Autonomous Coding Agents
- [OpenHands](https://openhands.dev/)
- [OpenHands Index (January 2026)](https://openhands.dev/blog/openhands-index)
- [SWE-bench SOTA with Inference-Time Scaling](https://openhands.dev/blog/sota-on-swe-bench-verified-with-inference-time-scaling-and-critic-model)
- [Cline - Autonomous Coding Agent](https://cline.bot/)
- [Aider - AI Pair Programming](https://aider.chat/)
- [claude-flow (GitHub)](https://github.com/ruvnet/claude-flow)

### Anthropic Announcements
- [Building Agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Enabling Claude Code to Work More Autonomously](https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously)
- [Advanced Tool Use on Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use)
- [Anthropic Cowork Research Preview](https://adtmag.com/articles/2026/01/20/anthropic-expands-claude-computer-agent-with-cowork.aspx)

### Additional Resources
- [Claude Code Multiple Agent Systems Guide (2026)](https://www.eesel.ai/blog/claude-code-multiple-agent-systems-complete-2026-guide)
- [Claude Code Agent Teams (Addy Osmani)](https://addyosmani.com/blog/claude-code-agent-teams/)
- [From Tasks to Swarms: Agent Teams in Claude Code](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/)
- [Claude Code Sub-Agents: Parallel vs Sequential Patterns](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
- [Best AI Coding Agents for 2026 (Faros AI)](https://www.faros.ai/blog/best-ai-coding-agents-2026)
- [Google ADK with A2A Protocol](https://google.github.io/adk-docs/a2a/)
