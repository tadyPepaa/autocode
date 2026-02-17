import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.research_runner import run_claude_message


@pytest.mark.asyncio
async def test_run_claude_first_message():
    """First message uses claude -p without -c flag."""
    fake_result = json.dumps({"type": "result", "result": "Hello from Claude"})
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (fake_result.encode(), b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await run_claude_message(
            workspace_path="/tmp/test",
            message="Hello",
            is_continuation=False,
        )

    assert result == "Hello from Claude"
    call_args = mock_exec.call_args[0]
    assert "-p" in call_args
    assert "Hello" in call_args
    assert "-c" not in call_args


@pytest.mark.asyncio
async def test_run_claude_continuation_message():
    """Subsequent messages use -c flag to continue conversation."""
    fake_result = json.dumps({"type": "result", "result": "Continued response"})
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (fake_result.encode(), b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await run_claude_message(
            workspace_path="/tmp/test",
            message="Continue",
            is_continuation=True,
        )

    assert result == "Continued response"
    call_args = mock_exec.call_args[0]
    assert "-c" in call_args


@pytest.mark.asyncio
async def test_run_claude_error():
    """Non-zero exit code raises RuntimeError."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"Error occurred")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="Claude CLI failed"):
            await run_claude_message("/tmp/test", "Hello", False)
