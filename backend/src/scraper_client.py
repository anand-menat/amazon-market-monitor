import os
import re
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import quote_plus

import requests

SCRAPERAPI_BASE_URL = "https://api.scraperapi.com/structured/amazon"
SCRAPERAPI_GENERIC_URL = "https://api.scraperapi.com"
logger = logging.getLogger(__name__)
DOMAIN_TO_COUNTRY = {
    "com": "us",
    "ca": "ca",
    "co.uk": "gb",
    "de": "de",
    "fr": "fr",
    "it": "it",
    "es": "es",
    "in": "in",
    "ae": "ae",
}
COUNTRY_TO_DOMAIN = {country: domain for domain, country in DOMAIN_TO_COUNTRY.items()}
ASIN_PATTERN = re.compile(r"(?:/dp/|/gp/product/|/product/)?([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE)


class ScraperApiError(RuntimeError):
    pass


def _with_retries(fn, retries: int = 3, label: str = "request"):
    """Execute *fn* with exponential-backoff retries."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return fn()
        except (requests.RequestException, ValueError) as exc:
            if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 404:
                raise ScraperApiError(f"Resource not found (404) for {label}")
            last_error = exc
            logger.warning(
                "ScraperAPI %s failed attempt=%s/%s error=%s",
                label,
                attempt + 1,
                retries,
                exc,
            )
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise ScraperApiError(f"ScraperAPI {label} failed: {last_error}")


def extract_asin(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        raise ScraperApiError("Provide an Amazon product URL or ASIN.")

    if re.fullmatch(r"[A-Z0-9]{10}", candidate, flags=re.IGNORECASE):
        return candidate.upper()

    match = ASIN_PATTERN.search(candidate)
    if match:
        return match.group(1).upper()

    raise ScraperApiError("Could not find a valid ASIN in the product URL.")


def _api_key() -> str:
    key = os.getenv("SCRAPERAPI_KEY")
    if not key:
        raise ScraperApiError("SCRAPERAPI_KEY is missing. Add it to backend/.env.")
    return key


def _resolve_marketplace(domain: str, country_code: str) -> tuple[str, str]:
    country = (country_code or DOMAIN_TO_COUNTRY.get(domain, "us")).lower()
    selected_domain = domain or COUNTRY_TO_DOMAIN.get(country, "com")

    if DOMAIN_TO_COUNTRY.get(selected_domain) != country and country in COUNTRY_TO_DOMAIN:
        selected_domain = COUNTRY_TO_DOMAIN[country]

    return selected_domain, country


def _request(endpoint: str, params: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    request_params = {"api_key": _api_key(), **params}

    def _do():
        response = requests.get(
            f"{SCRAPERAPI_BASE_URL}/{endpoint}",
            params=request_params,
            timeout=70,
        )
        response.raise_for_status()
        return response.json()

    return _with_retries(_do, retries=retries, label=f"structured/{endpoint}")


def _generic_request(url: str, retries: int = 3) -> dict[str, Any]:
    request_params = {
        "api_key": _api_key(),
        "url": url,
        "autoparse": "true",
    }

    def _do():
        response = requests.get(SCRAPERAPI_GENERIC_URL, params=request_params, timeout=70)
        response.raise_for_status()
        return response.json()

    return _with_retries(_do, retries=retries, label=f"generic url={url}")


def _html_request(url: str, retries: int = 3) -> str:
    request_params = {
        "api_key": _api_key(),
        "url": url,
        "render": "false",
    }

    def _do():
        response = requests.get(SCRAPERAPI_GENERIC_URL, params=request_params, timeout=70)
        response.raise_for_status()
        return response.text

    return _with_retries(_do, retries=retries, label=f"html url={url}")


def _deep_find(data: Any, names: tuple[str, ...]) -> Any:
    if isinstance(data, dict):
        for name in names:
            if name in data and data[name] not in (None, "", [], {}):
                return data[name]
        for value in data.values():
            found = _deep_find(value, names)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(data, list):
        for item in data:
            found = _deep_find(item, names)
            if found not in (None, "", [], {}):
                return found
    return None


def _clean_html_text(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _match_html(pattern: str, html: str) -> str | None:
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    return _clean_html_text(match.group(1)) if match else None


def _parse_amazon_html(html: str) -> dict[str, Any]:
    title = _match_html(r'id=["\']productTitle["\'][^>]*>(.*?)</span>', html)
    brand = _match_html(r'id=["\']bylineInfo["\'][^>]*>(.*?)</a>', html)

    price_text = (
        _match_html(r'<span[^>]*class=["\'][^"\']*a-price-whole[^"\']*["\'][^>]*>(.*?)</span>', html)
        or _match_html(r'<span[^>]*class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>(.*?)</span>', html)
    )
    fraction = _match_html(r'<span[^>]*class=["\'][^"\']*a-price-fraction[^"\']*["\'][^>]*>(.*?)</span>', html)
    if price_text and fraction and "." not in price_text:
        price_text = f"{price_text}.{fraction}"

    rating_text = (
        _match_html(r'id=["\']acrPopover["\'][^>]*title=["\']([^"\']+)', html)
        or _match_html(r'<span[^>]*class=["\'][^"\']*a-icon-alt[^"\']*["\'][^>]*>(.*?)</span>', html)
    )
    rating_match = re.search(r"\d+(?:\.\d+)?", rating_text or "")

    currency = None
    if price_text:
        if "₹" in price_text:
            currency = "INR"
        elif "$" in price_text:
            currency = "USD"
        elif "£" in price_text:
            currency = "GBP"
        elif "€" in price_text:
            currency = "EUR"

    return {
        "title": title,
        "brand": brand,
        "price": _to_float(price_text),
        "currency": currency,
        "rating": float(rating_match.group(0)) if rating_match else None,
    }


def _parse_search_html(html: str, marketplace_domain: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_asins: set[str] = set()

    blocks = re.findall(
        r'<div[^>]+data-asin=["\']([A-Z0-9]{10})["\'][^>]*>(.*?)(?=<div[^>]+data-asin=["\'][A-Z0-9]{10}["\']|</body>)',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for asin, block in blocks:
        asin = asin.upper()
        if asin in seen_asins:
            continue

        title = (
            _match_html(r'<h2[^>]*>.*?<span[^>]*>(.*?)</span>.*?</h2>', block)
            or _match_html(r'<a[^>]+class=["\'][^"\']*a-link-normal[^"\']*["\'][^>]*>.*?<span[^>]*>(.*?)</span>', block)
        )
        if not title:
            continue

        price_text = (
            _match_html(r'<span[^>]*class=["\'][^"\']*a-price-whole[^"\']*["\'][^>]*>(.*?)</span>', block)
            or _match_html(r'<span[^>]*class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>(.*?)</span>', block)
        )
        fraction = _match_html(r'<span[^>]*class=["\'][^"\']*a-price-fraction[^"\']*["\'][^>]*>(.*?)</span>', block)
        if price_text and fraction and "." not in price_text:
            price_text = f"{price_text}.{fraction}"

        rating_text = _match_html(r'<span[^>]*class=["\'][^"\']*a-icon-alt[^"\']*["\'][^>]*>(.*?)</span>', block)
        rating_match = re.search(r"\d+(?:\.\d+)?", rating_text or "")
        image = _match_html(r'<img[^>]+src=["\']([^"\']+)["\']', block)

        seen_asins.add(asin)
        results.append(
            {
                "asin": asin,
                "title": title,
                "price": _to_float(price_text),
                "rating": float(rating_match.group(0)) if rating_match else None,
                "url": f"https://www.amazon.{marketplace_domain}/dp/{asin}",
                "image": image,
            }
        )

    return results


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_float(value: Any) -> float | str | None:
    if value is None or isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        for token in ("₹", "$", "£", "€", "USD", "GBP", "EUR", "INR", "AED", "CA$"):
            cleaned = cleaned.replace(token, "")
        match = re.search(r"\d+(?:\.\d+)?", cleaned)
        try:
            return float(match.group(0)) if match else value
        except (AttributeError, ValueError):
            return value
    return value


def normalize_product(content: dict[str, Any], asin: str, domain: str, country_code: str) -> dict[str, Any]:
    category_path = _deep_find(content, ("category_path", "breadcrumbs", "categoryPath")) or []
    images = _deep_find(content, ("images", "image", "image_urls", "product_images")) or []
    price = _deep_find(
        content,
        (
            "price",
            "price_value",
            "current_price",
            "current_price_value",
            "sale_price",
            "deal_price",
            "buybox_price",
            "list_price",
        ),
    )
    rating = _deep_find(content, ("rating", "stars", "average_rating", "review_rating"))
    title = _deep_find(content, ("title", "name", "product_title", "product_name"))
    currency = _deep_find(content, ("currency", "currency_code", "price_currency"))

    return {
        "asin": _deep_find(content, ("asin", "product_asin")) or asin,
        "url": _deep_find(content, ("url", "product_url")),
        "brand": _deep_find(content, ("brand", "byline", "store")),
        "price": _to_float(price),
        "stock": _deep_find(content, ("stock", "availability")),
        "title": title,
        "rating": _to_float(rating),
        "images": _as_list(images),
        "categories": _as_list(_deep_find(content, ("category", "categories"))),
        "category_path": [str(item).strip() for item in _as_list(category_path) if item],
        "currency": currency,
        "buybox": _deep_find(content, ("buybox", "buybox_winner")) or [],
        "product_overview": _deep_find(content, ("product_overview", "feature_bullets", "bullets")) or [],
        "amazon_domain": domain,
        "country_code": country_code,
        "scraped_at": datetime.now().isoformat(),
    }


def scrape_product_details(asin: str, country_code: str = "us", domain: str = "com") -> dict[str, Any]:
    marketplace_domain, country = _resolve_marketplace(domain, country_code)
    amazon_url = f"https://www.amazon.{marketplace_domain}/dp/{asin}"
    logger.info("Scraping product asin=%s domain=%s country=%s", asin, marketplace_domain, country)
    try:
        content = _request(
            "product",
            {
                "asin": asin,
                "tld": marketplace_domain,
                "country": country,
            },
        )
    except ScraperApiError:
        content = _generic_request(amazon_url)

    product = normalize_product(content, asin=asin, domain=marketplace_domain, country_code=country)
    if not product.get("title") or product.get("price") is None or product.get("rating") is None:
        html_fields = _parse_amazon_html(_html_request(amazon_url))
        for key, value in html_fields.items():
            if product.get(key) in (None, "", [], {}) and value not in (None, "", [], {}):
                product[key] = value

    return product


def clean_product_name(title: str) -> str:
    title = title or ""
    for separator in (" - ", " | ", ","):
        if separator in title:
            title = title.split(separator)[0]
    return title.strip()


def _extract_search_items(content: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("search_results", "organic_results", "items"):
        if isinstance(content.get(key), list):
            return content[key]
    if isinstance(content.get("results"), list):
        return content["results"]
    if isinstance(content.get("results"), dict):
        results = content["results"]
        return [
            *results.get("organic", []),
            *results.get("organic_results", []),
            *results.get("paid", []),
            *results.get("sponsored", []),
        ]
    if isinstance(content.get("products"), list):
        return content["products"]
    return []


def search_competitors(
    query_title: str,
    domain: str,
    country_code: str = "us",
    pages: int = 1,
) -> list[dict[str, Any]]:
    query = clean_product_name(query_title)
    marketplace_domain, country = _resolve_marketplace(domain, country_code)
    results: list[dict[str, Any]] = []
    seen_asins: set[str] = set()
    logger.info(
        "Searching competitors query=%r domain=%s country=%s pages=%s",
        query,
        marketplace_domain,
        country,
        pages,
    )

    for page in range(1, max(1, pages) + 1):
        try:
            content = _request(
                "search",
                {
                    "query": query,
                    "tld": marketplace_domain,
                    "country": country,
                    "page": page,
                },
            )
        except ScraperApiError:
            content = {}

        for item in _extract_search_items(content):
            asin = item.get("asin") or item.get("product_asin") or item.get("data_asin")
            title = item.get("title") or item.get("name") or item.get("product_title")
            if not asin or not title or asin in seen_asins:
                continue

            seen_asins.add(asin)
            results.append(
                {
                    "asin": asin,
                    "title": title,
                    "price": _to_float(
                        item.get("price")
                        or item.get("price_value")
                        or item.get("current_price")
                        or item.get("current_price_value")
                    ),
                    "rating": _to_float(item.get("rating") or item.get("stars")),
                    "url": item.get("url") or item.get("product_url"),
                    "image": item.get("image") or item.get("thumbnail"),
                }
            )

        if not results:
            search_url = f"https://www.amazon.{marketplace_domain}/s?k={quote_plus(query)}&page={page}"
            html_results = _parse_search_html(_html_request(search_url), marketplace_domain)
            for item in html_results:
                asin = item.get("asin")
                if not asin or asin in seen_asins:
                    continue

                seen_asins.add(asin)
                results.append(item)

        time.sleep(0.2)

    return results


def scrape_multiple_products(
    asins: list[str],
    country_code: str = "us",
    domain: str = "com",
) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(scrape_product_details, asin, country_code, domain): asin
            for asin in asins
        }
        for future in as_completed(futures):
            try:
                products.append(future.result())
            except ScraperApiError:
                logger.warning("Skipped failed product asin=%s", futures[future])
    return products
