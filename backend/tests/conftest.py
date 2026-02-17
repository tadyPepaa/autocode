import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.auth import hash_password
from app.database import get_session
from app.main import app
from app.models.user import User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed admin user
        admin = User(
            username="admin",
            password_hash=hash_password("admin"),
            role="admin",
        )
        session.add(admin)
        session.commit()
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    return response.json()["access_token"]


@pytest.fixture
def user_token(client: TestClient, session: Session) -> str:
    user = User(
        username="testuser",
        password_hash=hash_password("testpass"),
        role="user",
    )
    session.add(user)
    session.commit()
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass"},
    )
    return response.json()["access_token"]
