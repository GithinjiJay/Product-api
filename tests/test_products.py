import pytest


def test_create_product(client, auth_headers):
    """Test creating a product."""

    product_data = {
        "name": "Test Product",
        "description": "This is a test product",
        "price": 99.99,
        "stock": 10
    }

    response = client.post(
        "/products",
        json=product_data,
        headers=auth_headers
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"]


def test_list_products(client, auth_headers):
    """Test listing products."""

    product_data = {
        "name": "Test Product",
        "description": "This is a test product",
        "price": 99.99,
        "stock": 10
    }

    # Create product first
    client.post(
        "/products",
        json=product_data,
        headers=auth_headers
    )

    # Get products
    response = client.get(
        "/products",
        headers=auth_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1
    assert any(product["name"] == product_data["name"] for product in data)


def test_get_product(client, auth_headers):
    """Test getting a single product."""

    product_data = {
        "name": "Test Product",
        "description": "This is a test product",
        "price": 99.99,
        "stock": 10
    }

    # Create product
    create_response = client.post(
        "/products",
        json=product_data,
        headers=auth_headers
    )

    product_id = create_response.json()["id"]

    # Get product
    response = client.get(
        f"/products/{product_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == product_data["name"]


def test_get_product_not_found(client, auth_headers):
    """Test getting a non-existent product."""

    response = client.get(
        "/products/99999",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_update_product(client, auth_headers):
    """Test updating a product."""

    product_data = {
        "name": "Test Product",
        "description": "This is a test product",
        "price": 99.99,
        "stock": 10
    }

    # Create product
    create_response = client.post(
        "/products",
        json=product_data,
        headers=auth_headers
    )

    product_id = create_response.json()["id"]

    # Update product
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


def test_delete_product(client, auth_headers):
    """Test deleting a product."""

    product_data = {
        "name": "Test Product",
        "description": "This is a test product",
        "price": 99.99,
        "stock": 10
    }

    # Create product
    create_response = client.post(
        "/products",
        json=product_data,
        headers=auth_headers
    )

    product_id = create_response.json()["id"]

    # Delete product
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