from fastapi.testclient import TestClient


def test_login_success(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "nope"},
    )
    assert response.status_code == 401


def test_refresh_token(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    refresh_token = login.json()["refresh_token"]
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_with_invalid_token(client: TestClient):
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


def test_protected_endpoint_without_token(client: TestClient):
    response = client.get("/api/agents")
    assert response.status_code in [401, 403]


def test_protected_endpoint_with_token(client: TestClient, admin_token: str):
    response = client.get(
        "/api/agents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # 404 since agents route isn't created yet, but should not be 401
    assert response.status_code != 401
