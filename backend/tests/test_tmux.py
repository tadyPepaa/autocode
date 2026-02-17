import shutil
import time

import pytest

from app.services.tmux import TmuxManager

# Skip all tests if tmux is not available
pytestmark = pytest.mark.skipif(
    not shutil.which("tmux"), reason="tmux not installed"
)


@pytest.fixture
def tmux():
    manager = TmuxManager()
    sessions: list[str] = []
    yield manager, sessions
    # Cleanup: kill all test sessions
    for s in sessions:
        manager.kill_session(s)


def test_create_and_exists(tmux):
    manager, sessions = tmux
    sessions.append("test-autocode-create")
    manager.create_session("test-autocode-create", "/tmp")
    assert manager.session_exists("test-autocode-create")


def test_send_keys_and_capture(tmux):
    manager, sessions = tmux
    sessions.append("test-autocode-capture")
    manager.create_session("test-autocode-capture", "/tmp")
    manager.send_keys("test-autocode-capture", "echo hello-autocode-test")
    time.sleep(0.5)
    output = manager.capture_pane("test-autocode-capture")
    assert "hello-autocode-test" in output


def test_kill_session(tmux):
    manager, sessions = tmux
    manager.create_session("test-autocode-kill", "/tmp")
    manager.kill_session("test-autocode-kill")
    assert not manager.session_exists("test-autocode-kill")


def test_list_sessions(tmux):
    manager, sessions = tmux
    sessions.append("test-autocode-list")
    manager.create_session("test-autocode-list", "/tmp")
    names = manager.list_sessions()
    assert "test-autocode-list" in names


def test_session_not_exists(tmux):
    manager, _ = tmux
    assert not manager.session_exists("nonexistent-session-xyz")
