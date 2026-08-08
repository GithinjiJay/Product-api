import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from main import app, get_session

# Create a test database
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""

    def get_test_session():
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    """Create a test user."""

    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for protected endpoints."""

    # Register user
    client.post("/register", json=test_user)

    # Login user
    response = client.post(
        "/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }