AVAILABLE_MODELS = [
    {"id": "gpt-5.2-codex", "name": "GPT-5.2 Codex", "category": "coding"},
    {"id": "gpt-5.2", "name": "GPT-5.2", "category": "general"},
    {"id": "gpt-5.1-codex-max", "name": "GPT-5.1 Codex Max", "category": "coding"},
    {"id": "gpt-5.1-codex", "name": "GPT-5.1 Codex", "category": "coding"},
    {"id": "gpt-5.1-codex-mini", "name": "GPT-5.1 Codex Mini", "category": "coding"},
    {"id": "gpt-5.1", "name": "GPT-5.1", "category": "general"},
    {"id": "codex-mini-latest", "name": "Codex Mini", "category": "coding"},
]

TEMPLATES = {
    "coding": {
        "type": "coding",
        "name": "Coding Agent",
        "model": "gpt-5.2-codex",
        "identity": (
            "You are a coding agent. Your job is to manage Claude Code via tmux "
            "and implement projects autonomously. Always:\n"
            "- Break work into small steps\n"
            "- Verify results after each step\n"
            "- Try 3 different approaches before escalating\n"
            "- Use conventional commits"
        ),
        "tools": '["tmux", "exec", "read_file", "write_file", "web_search"]',
        "global_rules": (
            "- Conventional commits (feat:, fix:, chore:, docs:, refactor:)\n"
            "- Write tests for business logic\n"
            "- Never commit secrets\n"
            "- Atomic commits\n"
            "- Code review before merge to main"
        ),
    },
    "research": {
        "type": "research",
        "name": "Research Agent",
        "model": "gpt-5.2",
        "identity": (
            "You are a research agent. Search the web, analyze information, "
            "and provide structured reports with source citations. Be thorough "
            "and verify claims from multiple sources."
        ),
        "tools": "[]",
        "global_rules": "",
    },
    "learning": {
        "type": "learning",
        "name": "Learning Tutor",
        "model": "gpt-5.2",
        "identity": (
            "You are a personalized tutor. Adapt to the student's level, "
            "track their progress, correct mistakes gently with explanations. "
            "Be patient and encouraging. Always update student_notes.md after "
            "each session."
        ),
        "tools": '["web_search", "web_fetch", "read_file", "write_file"]',
        "global_rules": "",
    },
    "social_media": {
        "type": "social_media",
        "name": "Social Media",
        "model": "gpt-5.1",
        "identity": (
            "You are a social media content assistant. Help create engaging "
            "posts, suggest hashtags, write captions. Maintain the user's "
            "brand voice. Be creative but professional."
        ),
        "tools": "[]",
        "global_rules": "",
    },
}


def get_template(name: str) -> dict | None:
    return TEMPLATES.get(name)


def list_templates() -> list[str]:
    return list(TEMPLATES.keys())
