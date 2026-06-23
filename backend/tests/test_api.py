import os

from fastapi.testclient import TestClient

import main


def test_health_endpoint():
    with TestClient(main.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scrape_endpoint_returns_product(monkeypatch):
    monkeypatch.setattr(
        main,
        "scrape_and_store_product",
        lambda asin, country_code, domain: {
            "asin": asin,
            "title": "Portable SSD 1TB",
            "price": 99.5,
            "amazon_domain": domain,
            "country_code": country_code,
        },
    )

    with TestClient(main.app) as client:
        response = client.post(
            "/api/products/scrape",
            json={"asin": "B0CX23VSAS", "domain": "com", "country_code": "us"},
        )

    assert response.status_code == 200
    assert response.json()["asin"] == "B0CX23VSAS"


def test_list_products_returns_paginated(monkeypatch, tmp_path):
    from src.db import Database

    db = Database(tmp_path / "data.json")
    db.upsert_product({"asin": "B000TEST01", "title": "Test Product"})
    monkeypatch.setattr(main, "Database", lambda: db)

    with TestClient(main.app) as client:
        response = client.get("/api/products?page=1&per_page=10")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert "items" in data


def test_delete_product_endpoint(monkeypatch, tmp_path):
    from src.db import Database

    db = Database(tmp_path / "data.json")
    db.upsert_product({"asin": "B000DEL001", "title": "To Delete"})
    monkeypatch.setattr(main, "Database", lambda: db)

    with TestClient(main.app) as client:
        response = client.delete("/api/products/B000DEL001")

    assert response.status_code == 200
    assert response.json()["deleted"] >= 1


def test_get_product_not_found(monkeypatch, tmp_path):
    from src.db import Database

    db = Database(tmp_path / "data.json")
    monkeypatch.setattr(main, "Database", lambda: db)

    with TestClient(main.app) as client:
        response = client.get("/api/products/BNOTEXISTS")

    assert response.status_code == 404


def test_api_key_required_when_configured(monkeypatch):
    monkeypatch.setenv("APP_API_KEY", "test-secret-key")

    with TestClient(main.app) as client:
        # Request without key should fail
        response = client.get("/api/health")
        assert response.status_code == 403

        # Request with wrong key should fail
        response = client.get("/api/health", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403

        # Request with correct key should succeed
        response = client.get("/api/health", headers={"X-API-Key": "test-secret-key"})
        assert response.status_code == 200


def test_api_key_not_required_when_unconfigured(monkeypatch):
    monkeypatch.delenv("APP_API_KEY", raising=False)

    with TestClient(main.app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200

