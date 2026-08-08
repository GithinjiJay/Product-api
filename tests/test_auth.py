import pytest
from tests.conftest import client, test_user


def test_register_user(client, test_user):
    """Test user registration."""
    response = client.post("/register", json=test_user)

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert "password" not in data  # Password should not be returned


def test_register_duplicate_user(client, test_user):
    """Test registering with an existing username."""

    # First registration
    client.post("/register", json=test_user)

    # Second registration with same username
    duplicate_user = test_user.copy()
    duplicate_user["email"] = "different@example.com"

    response = client.post("/register", json=duplicate_user)

    assert response.status_code == 409  # Conflict
    assert "username already exists" in response.text.lower()


def test_login_user(client, test_user):
    """Test user login."""

    # Register first
    client.post("/register", json=test_user)

    # Login
    response = client.post(
        "/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, test_user):
    """Test login with invalid credentials."""

    # Register first
    client.post("/register", json=test_user)

    # Login with wrong password
    response = client.post(
        "/login",
        data={
            "username": test_user["username"],
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401