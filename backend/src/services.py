import re
import logging
from datetime import datetime

from src.db import Database
from src.scraper_client import scrape_multiple_products, scrape_product_details, search_competitors


logger = logging.getLogger(__name__)


def scrape_and_store_product(asin: str, country_code: str, domain: str) -> dict:
    data = scrape_product_details(asin=asin, country_code=country_code, domain=domain)
    db = Database()
    db.upsert_product(data)
    db.record_price_snapshot(data)
    logger.info("Stored product asin=%s price=%s", data.get("asin"), data.get("price"))
    return data


def run_product_workflow(
    asin: str,
    country_code: str,
    domain: str,
    with_competitors: bool = True,
    pages: int = 2,
) -> dict:
    product = scrape_and_store_product(asin=asin, country_code=country_code, domain=domain)
    competitors = []
    if with_competitors:
        competitors = fetch_and_store_competitors(
            parent_asin=asin,
            domain=domain,
            country_code=country_code,
            pages=pages,
        )

    return {
        "product": product,
        "competitors": competitors,
        "competitors_found": len(competitors),
    }


def get_stored_competitors(parent_asin: str) -> list[dict]:
    return Database().search_products({"parent_asin": parent_asin})


def _extract_capacity(title: str) -> str:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s?(TB|GB)\b", title, flags=re.IGNORECASE)
    return f"{match.group(1)}{match.group(2).upper()}" if match else ""


def _infer_product_search_query(parent: dict) -> str:
    title = str(parent.get("title") or "")
    lower_title = title.lower()
    capacity = _extract_capacity(title)

    if "ssd" in lower_title or "solid state drive" in lower_title:
        traits = []
        if "portable" in lower_title:
            traits.append("portable")
        if "external" in lower_title or "portable" in lower_title:
            traits.append("external")
        if "internal" in lower_title:
            traits.append("internal")
        if "nvme" in lower_title:
            traits.append("nvme")
        if "m.2" in lower_title or "m2" in lower_title:
            traits.append("m.2")

        query_parts = [capacity, *dict.fromkeys(traits), "SSD"]
        return " ".join(part for part in query_parts if part)

    if "hard drive" in lower_title or "hdd" in lower_title:
        traits = ["external"] if "external" in lower_title or "portable" in lower_title else []
        query_parts = [capacity, *traits, "hard drive"]
        return " ".join(part for part in query_parts if part)

    return ""


def _build_search_queries(parent: dict, fallback_asin: str) -> list[str]:
    queries: list[str] = []
    inferred_query = _infer_product_search_query(parent)
    if inferred_query:
        queries.append(inferred_query)

    title_text = str(parent.get("title") or "")
    capacity = _extract_capacity(title_text)
    lower_title = title_text.lower()
    if "ssd" in lower_title or "solid state drive" in lower_title:
        for query in (
            f"{capacity} external SSD",
            f"{capacity} portable SSD",
            f"{capacity} solid state drive",
            "external SSD",
        ):
            if query.strip():
                queries.append(query.strip())

    title = parent.get("title")
    if title:
        queries.append(title)

    brand = (parent.get("brand") or "").replace("Visit the", "").replace("Store", "").strip()
    categories = parent.get("category_path") or parent.get("categories") or []
    category = str(categories[-1]) if categories else ""
    query = " ".join(part for part in (brand, category) if part)
    if query:
        queries.append(query)

    queries.append(fallback_asin)
    return list(dict.fromkeys(queries))


def fetch_and_store_competitors(
    parent_asin: str,
    domain: str,
    country_code: str,
    pages: int = 2,
) -> list[dict]:
    db = Database()
    parent = db.get_product(parent_asin)
    if not parent:
        logger.warning("Cannot fetch competitors because parent product is missing asin=%s", parent_asin)
        return []

    search_domain = parent.get("amazon_domain") or domain
    search_country = parent.get("country_code") or country_code

    search_results = []
    for search_query in _build_search_queries(parent, parent_asin):
        search_results = search_competitors(
            query_title=search_query,
            domain=search_domain,
            country_code=search_country,
            pages=pages,
        )
        if any(result.get("asin") and result.get("asin") != parent_asin for result in search_results):
            break

    competitor_asins = [
        result["asin"]
        for result in search_results
        if result.get("asin") and result.get("asin") != parent_asin
    ]

    unique_asins = list(dict.fromkeys(competitor_asins))[:20]
    product_details = scrape_multiple_products(unique_asins, country_code=search_country, domain=search_domain)
    detailed_asins = {product.get("asin") for product in product_details if product.get("asin")}
    search_summaries = [
        {
            "asin": result["asin"],
            "title": result.get("title"),
            "url": result.get("url"),
            "price": result.get("price"),
            "rating": result.get("rating"),
            "images": [result["image"]] if result.get("image") else [],
            "categories": [],
            "category_path": parent.get("category_path") or [],
            "amazon_domain": search_domain,
            "country_code": search_country,
            "scraped_at": datetime.now().isoformat(),
        }
        for result in search_results
        if result.get("asin") in unique_asins and result.get("asin") not in detailed_asins
    ]

    stored_competitors = []
    for competitor in [*product_details, *search_summaries]:
        competitor["parent_asin"] = parent_asin
        db.upsert_product(competitor)
        db.record_price_snapshot(competitor)
        stored_competitors.append(competitor)

    logger.info("Stored %s competitors parent_asin=%s", len(stored_competitors), parent_asin)
    return stored_competitors
