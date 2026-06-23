import pytest

from src.scraper_client import (
    ScraperApiError,
    _resolve_marketplace,
    _to_float,
    clean_product_name,
    extract_asin,
    normalize_product,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("B0CX23VSAS", "B0CX23VSAS"),
        ("https://www.amazon.com/dp/B0CX23VSAS", "B0CX23VSAS"),
        ("https://www.amazon.in/gp/product/B0CX23VSAS?th=1", "B0CX23VSAS"),
        ("https://www.amazon.co.uk/dp/B0CX23VSAS/ref=something", "B0CX23VSAS"),
    ],
)
def test_extract_asin_accepts_asin_and_urls(value, expected):
    assert extract_asin(value) == expected


def test_extract_asin_rejects_invalid_value():
    with pytest.raises(ScraperApiError):
        extract_asin("not an amazon product")


def test_extract_asin_rejects_empty_string():
    with pytest.raises(ScraperApiError):
        extract_asin("")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("$99.99", 99.99),
        ("₹1,299", 1299.0),
        ("£45.50", 45.50),
        ("€19.99", 19.99),
        ("CA$29.99", 29.99),
        ("1,499.00", 1499.0),
        (None, None),
        (42, 42),
        (99.5, 99.5),
        ("not a price", "not a price"),
    ],
)
def test_to_float(value, expected):
    assert _to_float(value) == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Samsung T7 - Portable SSD", "Samsung T7"),
        ("Western Digital | External HDD", "Western Digital"),
        ("Seagate, 2TB, USB-C", "Seagate"),
        ("Simple Title", "Simple Title"),
        ("", ""),
        (None, ""),
    ],
)
def test_clean_product_name(title, expected):
    assert clean_product_name(title) == expected


@pytest.mark.parametrize(
    ("domain", "country", "expected_domain", "expected_country"),
    [
        ("com", "us", "com", "us"),
        ("co.uk", "gb", "co.uk", "gb"),
        ("", "in", "in", "in"),
        ("com", "", "com", "us"),
        ("de", "de", "de", "de"),
    ],
)
def test_resolve_marketplace(domain, country, expected_domain, expected_country):
    result_domain, result_country = _resolve_marketplace(domain, country)
    assert result_domain == expected_domain
    assert result_country == expected_country


def test_normalize_product_maps_common_scraper_fields():
    product = normalize_product(
        {
            "product_asin": "B0CX23VSAS",
            "product_title": "Portable SSD 1TB",
            "current_price": "$99.50",
            "review_rating": "4.6 out of 5",
            "image_urls": ["https://example.com/ssd.jpg"],
            "feature_bullets": ["Fast USB-C storage"],
        },
        asin="B0CX23VSAS",
        domain="com",
        country_code="us",
    )

    assert product["asin"] == "B0CX23VSAS"
    assert product["title"] == "Portable SSD 1TB"
    assert product["price"] == 99.5
    assert product["rating"] == 4.6
    assert product["images"] == ["https://example.com/ssd.jpg"]
    assert product["amazon_domain"] == "com"
    assert product["country_code"] == "us"


def test_normalize_product_handles_missing_fields():
    product = normalize_product({}, asin="B000TEST01", domain="com", country_code="us")

    assert product["asin"] == "B000TEST01"
    assert product["title"] is None
    assert product["price"] is None
    assert product["images"] == []

