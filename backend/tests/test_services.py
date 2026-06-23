from src import services
from src.db import Database


def test_scrape_and_store_product_records_price_snapshot(monkeypatch, tmp_path):
    db = Database(tmp_path / "data.json")

    monkeypatch.setattr(services, "Database", lambda: db)
    monkeypatch.setattr(
        services,
        "scrape_product_details",
        lambda asin, country_code, domain: {
            "asin": asin,
            "title": "Portable SSD 1TB",
            "price": 99.5,
            "currency": "USD",
            "rating": 4.6,
            "amazon_domain": domain,
            "country_code": country_code,
            "scraped_at": "2026-06-19T10:00:00",
        },
    )

    product = services.scrape_and_store_product("B0CX23VSAS", "us", "com")

    assert product["asin"] == "B0CX23VSAS"
    assert db.get_product("B0CX23VSAS")["title"] == "Portable SSD 1TB"
    assert db.get_price_history("B0CX23VSAS")[0]["price"] == 99.5


def test_fetch_and_store_competitors_uses_parent_search_context(monkeypatch, tmp_path):
    db = Database(tmp_path / "data.json")
    db.upsert_product(
        {
            "asin": "B0PARENT01",
            "title": "Acme 1TB Portable SSD",
            "amazon_domain": "com",
            "country_code": "us",
            "category_path": ["Electronics", "External Solid State Drives"],
        }
    )

    monkeypatch.setattr(services, "Database", lambda: db)
    monkeypatch.setattr(
        services,
        "search_competitors",
        lambda query_title, domain, country_code, pages: [
            {"asin": "B0COMP0001", "title": "Rival 1TB Portable SSD", "price": 89.0}
        ],
    )
    monkeypatch.setattr(
        services,
        "scrape_multiple_products",
        lambda asins, country_code, domain: [
            {
                "asin": asins[0],
                "title": "Rival 1TB Portable SSD",
                "price": 89.0,
                "currency": "USD",
                "amazon_domain": domain,
                "country_code": country_code,
                "scraped_at": "2026-06-19T10:05:00",
            }
        ],
    )

    competitors = services.fetch_and_store_competitors("B0PARENT01", "com", "us", pages=1)

    assert len(competitors) == 1
    assert competitors[0]["parent_asin"] == "B0PARENT01"
    assert db.get_product("B0COMP0001")["price"] == 89.0
