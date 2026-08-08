import pytest
from tests.conftest import client, test_user


def test_404_error(client):
    """Test 404 error handling."""

    response = client.get("/non-existent-endpoint")

    assert response.status_code == 404

    data = response.json()

    assert data["error"] is True
    assert "message" in data


def test_validation_error(client, auth_headers):
    """Test validation error handling."""

    # Create a product with invalid data
    product_data = {
        "name": "",  # Empty name should fail
        "description": "This is a test product",
        "price": -10,  # Negative price should fail
        "stock": -5  # Negative stock should fail
    }

    response = client.post(
        "/products",
        json=product_data,
        headers=auth_headers
    )

    assert response.status_code in [400, 422]  # Validation error

    data = response.json()

    assert data["error"] is True


def test_unauthorized_access(client):
    """Test unauthorized access to protected endpoints."""

    response = client.get("/users")

    assert response.status_code == 401  # Unauthorized


def test_forbidden_access(client, test_user, auth_headers):
    """Test forbidden access to admin-only endpoints."""

    # Regular user (not admin) tries to access admin endpoint
    response = client.get(
        "/users",
        headers=auth_headers
    )

    assert response.status_code == 403  # Forbidden