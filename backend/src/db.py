import os
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data.json"


class Database:
    def __init__(self, db_path: str | Path | None = None):
        path = Path(db_path or os.getenv("APP_DB_PATH", DEFAULT_DB_PATH))
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(path)
        self.products = self.db.table("products")
        self.price_history = self.db.table("price_history")
        self.jobs = self.db.table("jobs")
        self.job_runs = self.db.table("job_runs")
        self.analyses = self.db.table("analyses")

    def upsert_product(self, product_data: dict[str, Any]) -> list[int]:
        asin = product_data.get("asin")
        if not asin:
            raise ValueError("Product data must include asin")

        now = datetime.now().isoformat()
        existing = self.get_product(asin)
        payload = {**product_data, "updated_at": now}
        if not existing:
            payload["created_at"] = now

        Product = Query()
        return self.products.upsert(payload, Product.asin == asin)

    def insert_product(self, product_data: dict[str, Any]) -> list[int]:
        return self.upsert_product(product_data)

    def record_price_snapshot(self, product_data: dict[str, Any]) -> int:
        asin = product_data.get("asin")
        if not asin:
            raise ValueError("Product data must include asin")

        scraped_at = product_data.get("scraped_at") or datetime.now().isoformat()
        return self.price_history.insert(
            {
                "asin": asin,
                "price": product_data.get("price"),
                "currency": product_data.get("currency"),
                "rating": product_data.get("rating"),
                "stock": product_data.get("stock"),
                "scraped_at": scraped_at,
            }
        )

    def get_price_history(self, asin: str, limit: int = 50) -> list[dict[str, Any]]:
        Price = Query()
        snapshots = self.price_history.search(Price.asin == asin)
        sorted_snapshots = sorted(snapshots, key=lambda item: item.get("scraped_at", ""), reverse=True)
        return sorted_snapshots[:limit]

    def get_product(self, asin: str) -> dict[str, Any] | None:
        Product = Query()
        return self.products.get(Product.asin == asin)

    def get_all_products(self) -> list[dict[str, Any]]:
        return sorted(
            self.products.all(),
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )

    def get_products_paginated(self, page: int = 1, per_page: int = 10) -> dict[str, Any]:
        page = max(page, 1)
        per_page = min(max(per_page, 1), 100)
        products = self.get_all_products()
        total = len(products)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "items": products[start:end],
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": ceil(total / per_page) if total else 0,
        }

    def search_products(self, search_criteria: dict[str, Any]) -> list[dict[str, Any]]:
        Product = Query()
        query = None
        for key, value in search_criteria.items():
            part = Product[key] == value
            query = part if query is None else query & part

        return self.products.search(query) if query else []

    def delete_product(self, asin: str) -> int:
        Product = Query()
        products_to_remove = self.products.search((Product.asin == asin) | (Product.parent_asin == asin))
        asins_to_remove = {item.get("asin") for item in products_to_remove if item.get("asin")}
        removed = self.products.remove((Product.asin == asin) | (Product.parent_asin == asin))
        Price = Query()
        for removed_asin in asins_to_remove:
            self.price_history.remove(Price.asin == removed_asin)
        return len(removed)

    def delete_all_products(self) -> int:
        count = len(self.products.all())
        self.products.truncate()
        self.price_history.truncate()
        self.analyses.truncate()
        return count

    def create_job(self, job: dict[str, Any]) -> int:
        now = datetime.now().isoformat()
        return self.jobs.insert({**job, "created_at": now, "updated_at": now})

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        return self.jobs.get(doc_id=job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        return [{**job, "id": job.doc_id} for job in self.jobs.all()]

    def update_job(self, job_id: int, fields: dict[str, Any]) -> None:
        self.jobs.update({**fields, "updated_at": datetime.now().isoformat()}, doc_ids=[job_id])

    def delete_job(self, job_id: int) -> bool:
        return bool(self.jobs.remove(doc_ids=[job_id]))

    def insert_job_run(self, run: dict[str, Any]) -> int:
        return self.job_runs.insert(run)

    def list_job_runs(self, job_id: int | None = None, limit: int = 25) -> list[dict[str, Any]]:
        if job_id is None:
            runs = self.job_runs.all()
        else:
            Run = Query()
            runs = self.job_runs.search(Run.job_id == job_id)

        sorted_runs = sorted(runs, key=lambda item: item.get("started_at", ""), reverse=True)
        return [{**run, "id": run.doc_id} for run in sorted_runs[:limit]]

    def save_analysis(self, asin: str, result: dict[str, Any]) -> None:
        """Cache an LLM analysis result for a product."""
        Analysis = Query()
        self.analyses.upsert(
            {**result, "asin": asin, "cached_at": datetime.now().isoformat()},
            Analysis.asin == asin,
        )

    def get_cached_analysis(self, asin: str, max_age_minutes: int = 60) -> dict[str, Any] | None:
        """Return a cached analysis if it exists and is fresh enough."""
        Analysis = Query()
        record = self.analyses.get(Analysis.asin == asin)
        if not record:
            return None
        cached_at = record.get("cached_at")
        if not cached_at:
            return None
        try:
            age = (datetime.now() - datetime.fromisoformat(cached_at)).total_seconds()
            if age > max_age_minutes * 60:
                return None
        except (ValueError, TypeError):
            return None
        return record
