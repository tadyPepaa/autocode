from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.models.agent import Agent
from app.models.common import ApiKey, ChatMessage
from app.models.learning import LearningCourse, LearningSubject


@pytest.fixture
def data_dir(tmp_path):
    """Override settings.data_dir to use tmp_path for tests."""
    original = settings.data_dir
    settings.data_dir = str(tmp_path)
    yield tmp_path
    settings.data_dir = original


@pytest.fixture(autouse=True)
def mock_openai():
    """Mock OpenAI client for all learning tests."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is an AI tutor response."

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch(
        "app.api.learning.get_openai_client", return_value=mock_client
    ):
        yield mock_client


@pytest.fixture
def agent(session: Session, user_token: str, client: TestClient) -> dict:
    """Create a learning agent and return its data."""
    resp = client.post(
        "/api/agents",
        json={"template": "learning", "name": "Test Learning Agent"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==================== Subject CRUD ====================


class TestCreateSubject:
    def test_create_subject(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Mathematics"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Mathematics"
        assert data["slug"] == "mathematics"
        assert data["agent_id"] == agent["id"]
        assert "workspace_path" in data

        # Verify workspace was created
        workspace = Path(data["workspace_path"])
        assert workspace.exists()

    def test_create_subject_slug_generation(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Advanced Data Science!!! @#$"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        assert resp.json()["slug"] == "advanced-data-science"

    def test_create_subject_invalid_name(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "@#$%"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 400
        assert "Invalid subject name" in resp.json()["detail"]

    def test_create_subject_invalid_agent(
        self, client: TestClient, user_token: str, data_dir: Path
    ):
        resp = client.post(
            "/api/agents/9999/subjects",
            json={"name": "Physics"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_create_subject_workspace_path(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Computer Science"},
            headers=_auth(user_token),
        )
        data = resp.json()
        expected = str(data_dir / "testuser" / "learning" / "computer-science")
        assert data["workspace_path"] == expected


class TestListSubjects:
    def test_list_subjects(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Math"},
            headers=_auth(user_token),
        )
        client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Physics"},
            headers=_auth(user_token),
        )

        resp = client.get(
            f"/api/agents/{agent['id']}/subjects",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {s["name"] for s in data}
        assert "Math" in names
        assert "Physics" in names

    def test_list_subjects_empty(
        self, client: TestClient, user_token: str, agent: dict
    ):
        resp = client.get(
            f"/api/agents/{agent['id']}/subjects",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_subjects_invalid_agent(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/agents/9999/subjects",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404


class TestGetSubject:
    def test_get_subject(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        create_resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Biology"},
            headers=_auth(user_token),
        )
        subject_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/subjects/{subject_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == subject_id
        assert data["name"] == "Biology"

    def test_get_subject_not_found(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/subjects/9999",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404


class TestDeleteSubject:
    def test_delete_subject(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        create_resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Delete Me"},
            headers=_auth(user_token),
        )
        subject_id = create_resp.json()["id"]
        workspace_path = create_resp.json()["workspace_path"]

        assert Path(workspace_path).exists()

        resp = client.delete(
            f"/api/subjects/{subject_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Subject deleted"

        # Verify workspace cleaned up
        assert not Path(workspace_path).exists()

        # Verify subject is gone
        resp = client.get(
            f"/api/subjects/{subject_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_delete_subject_not_found(
        self, client: TestClient, user_token: str
    ):
        resp = client.delete(
            "/api/subjects/9999",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_delete_subject_cascades_courses_and_messages(
        self,
        client: TestClient,
        user_token: str,
        agent: dict,
        data_dir: Path,
        session: Session,
    ):
        # Create subject
        sub_resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "Cascade Test"},
            headers=_auth(user_token),
        )
        subject_id = sub_resp.json()["id"]

        # Create course
        course_resp = client.post(
            f"/api/subjects/{subject_id}/courses",
            json={"name": "Course A", "instructions": "Learn stuff"},
            headers=_auth(user_token),
        )
        course_id = course_resp.json()["id"]

        # Send a message
        client.post(
            f"/api/courses/{course_id}/message",
            json={"content": "Hello tutor"},
            headers=_auth(user_token),
        )

        # Verify message exists
        messages = session.exec(
            select(ChatMessage).where(
                ChatMessage.session_type == "learning",
                ChatMessage.session_id == course_id,
            )
        ).all()
        assert len(messages) == 2  # user + assistant

        # Delete subject
        client.delete(
            f"/api/subjects/{subject_id}",
            headers=_auth(user_token),
        )

        # Verify courses gone
        courses = session.exec(
            select(LearningCourse).where(
                LearningCourse.subject_id == subject_id,
            )
        ).all()
        assert len(courses) == 0

        # Verify messages gone
        messages = session.exec(
            select(ChatMessage).where(
                ChatMessage.session_type == "learning",
                ChatMessage.session_id == course_id,
            )
        ).all()
        assert len(messages) == 0


# ==================== Course CRUD ====================


def _create_subject(client, token, agent_id, name="Mathematics"):
    resp = client.post(
        f"/api/agents/{agent_id}/subjects",
        json={"name": name},
        headers=_auth(token),
    )
    return resp.json()


class TestCreateCourse:
    def test_create_course(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])

        resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Linear Algebra", "instructions": "Focus on vectors"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Linear Algebra"
        assert data["slug"] == "linear-algebra"
        assert data["instructions"] == "Focus on vectors"
        assert data["subject_id"] == subject["id"]

        # Verify workspace files
        course_dir = Path(data["workspace_path"])
        assert course_dir.exists()
        assert (course_dir / "chat_history.json").exists()
        assert (course_dir / "chat_history.json").read_text() == "[]"
        assert (course_dir / "student_notes.md").exists()
        assert (course_dir / "student_notes.md").read_text() == "# Student Notes\n"

    def test_create_course_default_instructions(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])

        resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Calculus"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        assert resp.json()["instructions"] == ""

    def test_create_course_invalid_name(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])

        resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "@#$%"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 400
        assert "Invalid course name" in resp.json()["detail"]

    def test_create_course_invalid_subject(
        self, client: TestClient, user_token: str, data_dir: Path
    ):
        resp = client.post(
            "/api/subjects/9999/courses",
            json={"name": "Ghost Course"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_create_course_workspace_path(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"], name="Math")

        resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Set Theory"},
            headers=_auth(user_token),
        )
        data = resp.json()
        expected = str(
            data_dir / "testuser" / "learning" / "math" / "set-theory"
        )
        assert data["workspace_path"] == expected


class TestListCourses:
    def test_list_courses(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])

        client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Course A"},
            headers=_auth(user_token),
        )
        client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Course B"},
            headers=_auth(user_token),
        )

        resp = client.get(
            f"/api/subjects/{subject['id']}/courses",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {c["name"] for c in data}
        assert "Course A" in names
        assert "Course B" in names

    def test_list_courses_empty(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])

        resp = client.get(
            f"/api/subjects/{subject['id']}/courses",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_courses_invalid_subject(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/subjects/9999/courses",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404


class TestGetCourse:
    def test_get_course(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])
        create_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Topology", "instructions": "Open sets"},
            headers=_auth(user_token),
        )
        course_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/courses/{course_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == course_id
        assert data["name"] == "Topology"
        assert data["instructions"] == "Open sets"

    def test_get_course_not_found(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/courses/9999",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404


class TestDeleteCourse:
    def test_delete_course(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])
        create_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Delete Course"},
            headers=_auth(user_token),
        )
        course_id = create_resp.json()["id"]
        workspace_path = create_resp.json()["workspace_path"]

        assert Path(workspace_path).exists()

        resp = client.delete(
            f"/api/courses/{course_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Course deleted"

        # Verify workspace cleaned up
        assert not Path(workspace_path).exists()

        # Verify course is gone
        resp = client.get(
            f"/api/courses/{course_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_delete_course_not_found(
        self, client: TestClient, user_token: str
    ):
        resp = client.delete(
            "/api/courses/9999",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_delete_course_cleans_chat_messages(
        self,
        client: TestClient,
        user_token: str,
        agent: dict,
        data_dir: Path,
        session: Session,
    ):
        subject = _create_subject(client, user_token, agent["id"])
        create_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Msg Cleanup"},
            headers=_auth(user_token),
        )
        course_id = create_resp.json()["id"]

        # Send a message (creates user + assistant messages)
        client.post(
            f"/api/courses/{course_id}/message",
            json={"content": "Hello tutor"},
            headers=_auth(user_token),
        )

        # Verify messages exist
        messages = session.exec(
            select(ChatMessage).where(
                ChatMessage.session_type == "learning",
                ChatMessage.session_id == course_id,
            )
        ).all()
        assert len(messages) == 2

        # Delete course
        client.delete(
            f"/api/courses/{course_id}",
            headers=_auth(user_token),
        )

        # Verify messages cleaned up
        messages = session.exec(
            select(ChatMessage).where(
                ChatMessage.session_type == "learning",
                ChatMessage.session_id == course_id,
            )
        ).all()
        assert len(messages) == 0


# ==================== Chat ====================


class TestSendMessage:
    def test_send_message(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])
        course_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Chat Course", "instructions": "Be helpful"},
            headers=_auth(user_token),
        )
        course_id = course_resp.json()["id"]

        resp = client.post(
            f"/api/courses/{course_id}/message",
            json={"content": "What is a vector?"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "message" in data
        assert data["message"] == "This is an AI tutor response."

    def test_send_message_stores_both_roles(
        self,
        client: TestClient,
        user_token: str,
        agent: dict,
        data_dir: Path,
        session: Session,
    ):
        subject = _create_subject(client, user_token, agent["id"])
        course_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "DB Chat"},
            headers=_auth(user_token),
        )
        course_id = course_resp.json()["id"]

        client.post(
            f"/api/courses/{course_id}/message",
            json={"content": "Test message"},
            headers=_auth(user_token),
        )

        messages = session.exec(
            select(ChatMessage)
            .where(
                ChatMessage.session_type == "learning",
                ChatMessage.session_id == course_id,
            )
            .order_by(ChatMessage.created_at)
        ).all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Test message"
        assert messages[1].role == "assistant"
        assert messages[1].content == "This is an AI tutor response."

    def test_send_message_not_found(
        self, client: TestClient, user_token: str
    ):
        resp = client.post(
            "/api/courses/9999/message",
            json={"content": "Hello"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_send_multiple_messages(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])
        course_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Multi Chat"},
            headers=_auth(user_token),
        )
        course_id = course_resp.json()["id"]

        # Send multiple messages
        for i in range(3):
            resp = client.post(
                f"/api/courses/{course_id}/message",
                json={"content": f"Message {i}"},
                headers=_auth(user_token),
            )
            assert resp.status_code == 201

        # Check history
        resp = client.get(
            f"/api/courses/{course_id}/messages",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        messages = resp.json()
        # 3 user + 3 assistant = 6 messages
        assert len(messages) == 6


class TestGetMessages:
    def test_get_messages(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])
        course_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "History Course"},
            headers=_auth(user_token),
        )
        course_id = course_resp.json()["id"]

        client.post(
            f"/api/courses/{course_id}/message",
            json={"content": "First question"},
            headers=_auth(user_token),
        )

        resp = client.get(
            f"/api/courses/{course_id}/messages",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        messages = resp.json()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "First question"
        assert messages[1]["role"] == "assistant"

    def test_get_messages_empty(
        self, client: TestClient, user_token: str, agent: dict, data_dir: Path
    ):
        subject = _create_subject(client, user_token, agent["id"])
        course_resp = client.post(
            f"/api/subjects/{subject['id']}/courses",
            json={"name": "Empty Chat"},
            headers=_auth(user_token),
        )
        course_id = course_resp.json()["id"]

        resp = client.get(
            f"/api/courses/{course_id}/messages",
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_messages_not_found(
        self, client: TestClient, user_token: str
    ):
        resp = client.get(
            "/api/courses/9999/messages",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404


# ==================== User Isolation ====================


class TestUserIsolation:
    def test_cannot_access_other_users_subject(
        self,
        client: TestClient,
        user_token: str,
        admin_token: str,
        data_dir: Path,
    ):
        # Admin creates agent and subject
        agent_resp = client.post(
            "/api/agents",
            json={"template": "learning", "name": "Admin Learning Agent"},
            headers=_auth(admin_token),
        )
        admin_agent_id = agent_resp.json()["id"]

        sub_resp = client.post(
            f"/api/agents/{admin_agent_id}/subjects",
            json={"name": "Admin Subject"},
            headers=_auth(admin_token),
        )
        subject_id = sub_resp.json()["id"]

        # User tries to get it
        resp = client.get(
            f"/api/subjects/{subject_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

        # User tries to delete it
        resp = client.delete(
            f"/api/subjects/{subject_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_cannot_access_other_users_course(
        self,
        client: TestClient,
        user_token: str,
        admin_token: str,
        data_dir: Path,
    ):
        # Admin creates agent, subject, course
        agent_resp = client.post(
            "/api/agents",
            json={"template": "learning", "name": "Admin Agent 2"},
            headers=_auth(admin_token),
        )
        admin_agent_id = agent_resp.json()["id"]

        sub_resp = client.post(
            f"/api/agents/{admin_agent_id}/subjects",
            json={"name": "Admin Subject 2"},
            headers=_auth(admin_token),
        )
        subject_id = sub_resp.json()["id"]

        course_resp = client.post(
            f"/api/subjects/{subject_id}/courses",
            json={"name": "Admin Course"},
            headers=_auth(admin_token),
        )
        course_id = course_resp.json()["id"]

        # User tries to get course
        resp = client.get(
            f"/api/courses/{course_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

        # User tries to delete course
        resp = client.delete(
            f"/api/courses/{course_id}",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

        # User tries to send message
        resp = client.post(
            f"/api/courses/{course_id}/message",
            json={"content": "Hacked"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

        # User tries to get messages
        resp = client.get(
            f"/api/courses/{course_id}/messages",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_cannot_list_other_users_subjects(
        self,
        client: TestClient,
        user_token: str,
        admin_token: str,
        data_dir: Path,
    ):
        # Admin creates agent
        agent_resp = client.post(
            "/api/agents",
            json={"template": "learning", "name": "Admin Agent 3"},
            headers=_auth(admin_token),
        )
        admin_agent_id = agent_resp.json()["id"]

        # Admin creates subject
        client.post(
            f"/api/agents/{admin_agent_id}/subjects",
            json={"name": "Secret Subject"},
            headers=_auth(admin_token),
        )

        # User tries to list admin's subjects - should get 404 (not their agent)
        resp = client.get(
            f"/api/agents/{admin_agent_id}/subjects",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_cannot_list_other_users_courses(
        self,
        client: TestClient,
        user_token: str,
        admin_token: str,
        data_dir: Path,
    ):
        # Admin creates full chain
        agent_resp = client.post(
            "/api/agents",
            json={"template": "learning", "name": "Admin Agent 4"},
            headers=_auth(admin_token),
        )
        admin_agent_id = agent_resp.json()["id"]

        sub_resp = client.post(
            f"/api/agents/{admin_agent_id}/subjects",
            json={"name": "Admin Sub"},
            headers=_auth(admin_token),
        )
        admin_subject_id = sub_resp.json()["id"]

        # User tries to list courses for admin's subject
        resp = client.get(
            f"/api/subjects/{admin_subject_id}/courses",
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_cannot_create_subject_for_other_users_agent(
        self,
        client: TestClient,
        user_token: str,
        admin_token: str,
        data_dir: Path,
    ):
        # Admin creates agent
        agent_resp = client.post(
            "/api/agents",
            json={"template": "learning", "name": "Admin Agent 5"},
            headers=_auth(admin_token),
        )
        admin_agent_id = agent_resp.json()["id"]

        # User tries to create subject on admin's agent
        resp = client.post(
            f"/api/agents/{admin_agent_id}/subjects",
            json={"name": "Sneak Subject"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404

    def test_cannot_create_course_for_other_users_subject(
        self,
        client: TestClient,
        user_token: str,
        admin_token: str,
        data_dir: Path,
    ):
        # Admin creates full chain
        agent_resp = client.post(
            "/api/agents",
            json={"template": "learning", "name": "Admin Agent 6"},
            headers=_auth(admin_token),
        )
        admin_agent_id = agent_resp.json()["id"]

        sub_resp = client.post(
            f"/api/agents/{admin_agent_id}/subjects",
            json={"name": "Admin Sub 2"},
            headers=_auth(admin_token),
        )
        admin_subject_id = sub_resp.json()["id"]

        # User tries to create course on admin's subject
        resp = client.post(
            f"/api/subjects/{admin_subject_id}/courses",
            json={"name": "Sneak Course"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 404


# ==================== Auth Required ====================


class TestAuthRequired:
    def test_create_subject_requires_auth(
        self, client: TestClient, agent: dict
    ):
        resp = client.post(
            f"/api/agents/{agent['id']}/subjects",
            json={"name": "No Auth"},
        )
        assert resp.status_code in [401, 403]

    def test_list_subjects_requires_auth(
        self, client: TestClient, agent: dict
    ):
        resp = client.get(f"/api/agents/{agent['id']}/subjects")
        assert resp.status_code in [401, 403]

    def test_get_subject_requires_auth(self, client: TestClient):
        resp = client.get("/api/subjects/1")
        assert resp.status_code in [401, 403]

    def test_delete_subject_requires_auth(self, client: TestClient):
        resp = client.delete("/api/subjects/1")
        assert resp.status_code in [401, 403]

    def test_create_course_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/subjects/1/courses",
            json={"name": "No Auth"},
        )
        assert resp.status_code in [401, 403]

    def test_send_message_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/courses/1/message",
            json={"content": "No Auth"},
        )
        assert resp.status_code in [401, 403]

    def test_get_messages_requires_auth(self, client: TestClient):
        resp = client.get("/api/courses/1/messages")
        assert resp.status_code in [401, 403]
