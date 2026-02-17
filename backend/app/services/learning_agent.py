"""Learning agent service — stub for AI tutor functionality.

Provides a clean interface for LLM integration. Currently returns
placeholder responses; actual LLM calls will be plugged in later.
"""

from pathlib import Path


class LearningAgentService:
    """AI tutor service for learning courses."""

    async def get_response(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        new_message: str,
    ) -> str:
        """Generate a tutor response for the given message.

        Args:
            system_prompt: Combined agent identity + course instructions + notes.
            messages: Chat history as list of {"role": ..., "content": ...}.
            new_message: The new user message to respond to.

        Returns:
            AI tutor response string.
        """
        # Stub: will be replaced with actual LLM call
        return "I'm your AI tutor. LLM integration coming soon."

    def read_student_notes(self, notes_path: str) -> str:
        """Read student notes from the course workspace.

        Args:
            notes_path: Absolute path to student_notes.md file.

        Returns:
            Contents of the notes file, or empty string if not found.
        """
        path = Path(notes_path)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def compose_system_prompt(
        self,
        agent_identity: str,
        course_instructions: str,
        student_notes: str,
    ) -> str:
        """Build the system prompt from agent identity, course instructions, and notes.

        Args:
            agent_identity: The agent's identity/persona description.
            course_instructions: Course-specific instructions.
            student_notes: Current student notes content.

        Returns:
            Combined system prompt string.
        """
        parts = []
        if agent_identity:
            parts.append(f"## Identity\n{agent_identity}")
        if course_instructions:
            parts.append(f"## Course Instructions\n{course_instructions}")
        if student_notes:
            parts.append(f"## Student Notes\n{student_notes}")
        return "\n\n".join(parts) if parts else "You are an AI tutor."


learning_agent = LearningAgentService()
