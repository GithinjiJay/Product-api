import pytest


@pytest.mark.benchmark
def test_create_product_performance(client, auth_headers, benchmark):
    """Benchmark product creation performance."""

    product_data = {
        "name": "Performance Test Product",
        "description": "This is a test product for performance testing",
        "price": 99.99,
        "stock": 10
    }

    def create_product():
        response = client.post(
            "/products",
            json=product_data,
            headers=auth_headers
        )

        assert response.status_code == 201

    benchmark(create_product)