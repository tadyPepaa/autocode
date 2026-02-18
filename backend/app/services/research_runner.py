import asyncio
import json
import os


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

    # Remove CLAUDECODE env var to avoid nested session detection
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=workspace_path,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"Claude CLI failed (exit {proc.returncode}): {stderr.decode()}")

    data = json.loads(stdout.decode())
    return data.get("result", "")
