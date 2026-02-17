"""Learning agent service — AI tutor using ChatGPT subscription."""

from pathlib import Path

from app.services.openai_client import chatgpt_response


class LearningAgentService:
    """AI tutor service for learning courses."""

    async def get_response(
        self,
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        new_message: str,
    ) -> str:
        """Generate a tutor response using ChatGPT Responses API.

        Args:
            model: ChatGPT model ID (e.g. "gpt-5.2").
            system_prompt: Combined agent identity + course instructions + notes.
            messages: Chat history as list of {"role": ..., "content": ...}.
            new_message: The new user message to respond to.

        Returns:
            AI tutor response string.
        """
        input_messages = list(messages)
        input_messages.append({"role": "user", "content": new_message})

        return await chatgpt_response(
            model=model,
            instructions=system_prompt,
            messages=input_messages,
        )

    def read_student_notes(self, notes_path: str) -> str:
        """Read student notes from the course workspace."""
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
        """Build the system prompt from agent identity, course instructions, and notes."""
        parts = []
        if agent_identity:
            parts.append(f"## Identity\n{agent_identity}")
        if course_instructions:
            parts.append(f"## Course Instructions\n{course_instructions}")
        if student_notes:
            parts.append(f"## Student Notes\n{student_notes}")
        return "\n\n".join(parts) if parts else "You are an AI tutor."


learning_agent = LearningAgentService()
