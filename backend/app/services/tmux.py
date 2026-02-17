import subprocess


class TmuxManager:
    def create_session(self, name: str, working_dir: str) -> None:
        """Create a new detached tmux session."""
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", name, "-c", working_dir],
            check=True,
        )

    def kill_session(self, name: str) -> None:
        """Kill a tmux session. Ignores errors if session doesn't exist."""
        subprocess.run(["tmux", "kill-session", "-t", name], capture_output=True)

    def session_exists(self, name: str) -> bool:
        """Check if a tmux session exists."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True,
        )
        return result.returncode == 0

    def send_keys(self, name: str, keys: str) -> None:
        """Send keys to a tmux session."""
        subprocess.run(
            ["tmux", "send-keys", "-t", name, keys, "Enter"],
            check=True,
        )

    def capture_pane(self, name: str, lines: int = 200) -> str:
        """Capture the visible content of a tmux pane."""
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", name, "-p", "-S", f"-{lines}"],
            capture_output=True,
            text=True,
        )
        return result.stdout

    def list_sessions(self) -> list[str]:
        """List all tmux session names."""
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
