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
