"""Learning agent service — AI tutor using OpenAI."""

from pathlib import Path

from openai import AsyncOpenAI


class LearningAgentService:
    """AI tutor service for learning courses."""

    async def get_response(
        self,
        client: AsyncOpenAI,
        system_prompt: str,
        messages: list[dict[str, str]],
        new_message: str,
        model: str = "gpt-4o",
    ) -> str:
        """Generate a tutor response using OpenAI.

        Args:
            client: AsyncOpenAI client with user's API key.
            system_prompt: Combined agent identity + course instructions + notes.
            messages: Chat history as list of {"role": ..., "content": ...}.
            new_message: The new user message to respond to.
            model: OpenAI model to use.

        Returns:
            AI tutor response string.
        """
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})
        api_messages.append({"role": "user", "content": new_message})

        response = await client.chat.completions.create(
            model=model,
            messages=api_messages,
        )
        return response.choices[0].message.content or ""

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
