from tests.conftest import client


def test_full_crud_flow(client):
    """Test the full CRUD flow from registration to deletion."""

    # Create a user
    user_data = {
        "username": "integration_user",
        "email": "integration@example.com",
        "password": "password123",
        "full_name": "Integration User",
        "role": "user"
    }

    response = client.post("/register", json=user_data)

    assert response.status_code == 201

    # Login
    response = client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"]
        }
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    auth_headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create a product
    product_data = {
        "name": "Integration Product",
        "description": "This is an integration test product",
        "price": 99.99,
        "stock": 10
    }

    response = client.post(
        "/products",
        json=product_data,
        headers=auth_headers
    )

    assert response.status_code == 201

    product_id = response.json()["id"]

    # Update the product
    update_data = {
        "name": "Updated Product",
        "price": 149.99
    }

    response = client.patch(
        f"/products/{product_id}",
        json=update_data,
        headers=auth_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == update_data["name"]
    assert data["price"] == update_data["price"]

    # Delete the product
    response = client.delete(
        f"/products/{product_id}",
        headers=auth_headers
    )

    assert response.status_code == 204

    # Verify deletion
    response = client.get(
        f"/products/{product_id}",
        headers=auth_headers
    )

    assert response.status_code == 404