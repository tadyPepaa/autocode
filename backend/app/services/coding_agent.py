import asyncio
import logging

from app.services.tmux import TmuxManager

logger = logging.getLogger(__name__)


class CodingAgentLoop:
    def __init__(
        self,
        project_id: int,
        tmux_session: str,
        workspace: str,
        agent_config: dict,
    ):
        self.project_id = project_id
        self.tmux_session = tmux_session
        self.workspace = workspace
        self.agent_config = agent_config
        self.tmux = TmuxManager()
        self.running = False
        self.error_count = 0
        self.max_retries = 3

    async def start(self):
        self.running = True
        logger.info(f"Starting coding agent for project {self.project_id}")

        # Wait for Claude Code to initialize
        await asyncio.sleep(5)

        while self.running:
            step = self._get_current_step()
            if not step:
                logger.info(f"All steps done for project {self.project_id}")
                self._update_project_status("completed")
                break

            # Send task
            prompt = self._compose_prompt(step)
            self.tmux.send_keys(self.tmux_session, prompt)

            # Monitor
            output = await self._monitor_until_done()

            # Evaluate (simple for now - check if Claude Code returned to prompt)
            if self._claude_code_waiting_for_input(output):
                self._mark_step_done(step)
                self.error_count = 0
                logger.info(f"Step completed for project {self.project_id}")
            else:
                self.error_count += 1
                if self.error_count >= self.max_retries:
                    logger.warning(
                        f"Max retries reached for project {self.project_id}"
                    )
                    self._update_project_status("failed")
                    break

    async def _monitor_until_done(self, timeout: int = 300) -> str:
        elapsed = 0
        last_output = ""
        no_change_count = 0
        while elapsed < timeout:
            output = self.tmux.capture_pane(self.tmux_session)
            if self._claude_code_waiting_for_input(output):
                return output
            if output == last_output:
                no_change_count += 1
                if no_change_count > 150:  # 5 min with no change
                    return output
            else:
                no_change_count = 0
                last_output = output
            elapsed += 2
            await asyncio.sleep(2)
        return output

    def _claude_code_waiting_for_input(self, output: str) -> bool:
        lines = output.strip().split("\n")
        if not lines:
            return False
        last = lines[-1].strip()
        return last.endswith(">") or last.endswith("\u276f") or last.endswith("$")

    def _get_current_step(self) -> dict | None:
        # Will be implemented with DB access later
        # For now return None (no steps)
        return None

    def _compose_prompt(self, step: dict) -> str:
        return step.get("prompt", "")

    def _mark_step_done(self, step: dict):
        pass

    def _update_project_status(self, status: str):
        pass

    async def stop(self):
        self.running = False
        logger.info(f"Stopping coding agent for project {self.project_id}")
