"""Tests for the Database persistence layer."""

from src.db import Database


def test_upsert_and_retrieve_product(tmp_path):
    db = Database(tmp_path / "data.json")
    db.upsert_product({"asin": "B001234567", "title": "Test Widget", "price": 9.99})
    result = db.get_product("B001234567")

    assert result is not None
    assert result["title"] == "Test Widget"
    assert result["price"] == 9.99
    assert "created_at" in result
    assert "updated_at" in result


def test_upsert_updates_existing_product(tmp_path):
    db = Database(tmp_path / "data.json")
    db.upsert_product({"asin": "B001234567", "title": "Version 1", "price": 9.99})
    db.upsert_product({"asin": "B001234567", "title": "Version 2", "price": 14.99})
    result = db.get_product("B001234567")

    assert result["title"] == "Version 2"
    assert result["price"] == 14.99


def test_get_product_returns_none_for_missing(tmp_path):
    db = Database(tmp_path / "data.json")
    assert db.get_product("BNOTEXISTS") is None


def test_record_and_retrieve_price_snapshot(tmp_path):
    db = Database(tmp_path / "data.json")
    db.record_price_snapshot({"asin": "B001234567", "price": 9.99, "currency": "USD"})
    db.record_price_snapshot({"asin": "B001234567", "price": 8.99, "currency": "USD"})
    history = db.get_price_history("B001234567")

    assert len(history) == 2
    assert history[0]["price"] == 8.99  # most recent first


def test_get_price_history_respects_limit(tmp_path):
    db = Database(tmp_path / "data.json")
    for i in range(5):
        db.record_price_snapshot({
            "asin": "B001234567",
            "price": 10.0 + i,
            "scraped_at": f"2026-06-{20 + i:02d}T10:00:00",
        })

    history = db.get_price_history("B001234567", limit=3)
    assert len(history) == 3


def test_get_products_paginated(tmp_path):
    db = Database(tmp_path / "data.json")
    for i in range(15):
        db.upsert_product({"asin": f"B00000000{i:01d}" if i < 10 else f"B0000000{i:02d}", "title": f"Product {i}"})

    page1 = db.get_products_paginated(page=1, per_page=10)
    assert len(page1["items"]) == 10
    assert page1["total"] == 15
    assert page1["total_pages"] == 2

    page2 = db.get_products_paginated(page=2, per_page=10)
    assert len(page2["items"]) == 5


def test_delete_product_removes_product_and_children(tmp_path):
    db = Database(tmp_path / "data.json")
    db.upsert_product({"asin": "BPARENT001", "title": "Parent"})
    db.upsert_product({"asin": "BCHILD0001", "title": "Child", "parent_asin": "BPARENT001"})
    db.record_price_snapshot({"asin": "BPARENT001", "price": 10.0})
    db.record_price_snapshot({"asin": "BCHILD0001", "price": 5.0})

    deleted = db.delete_product("BPARENT001")

    assert deleted == 2
    assert db.get_product("BPARENT001") is None
    assert db.get_product("BCHILD0001") is None
    assert db.get_price_history("BPARENT001") == []
    assert db.get_price_history("BCHILD0001") == []


def test_job_crud(tmp_path):
    db = Database(tmp_path / "data.json")
    job_id = db.create_job({"name": "Test Job", "asin": "B001234567"})

    job = db.get_job(job_id)
    assert job is not None
    assert "created_at" in job

    jobs = db.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["id"] == job_id

    db.update_job(job_id, {"last_status": "success"})
    updated = db.get_job(job_id)
    assert updated["last_status"] == "success"

    deleted = db.delete_job(job_id)
    assert deleted is True
    assert db.get_job(job_id) is None


def test_job_run_history(tmp_path):
    db = Database(tmp_path / "data.json")
    run_id = db.insert_job_run({
        "job_id": 1,
        "status": "success",
        "started_at": "2026-06-20T10:00:00",
        "products_scraped": 1,
    })

    runs = db.list_job_runs()
    assert len(runs) == 1
    assert runs[0]["id"] == run_id

    runs_by_job = db.list_job_runs(job_id=1)
    assert len(runs_by_job) == 1

    runs_empty = db.list_job_runs(job_id=999)
    assert len(runs_empty) == 0


def test_analysis_cache(tmp_path):
    db = Database(tmp_path / "data.json")
    result = {
        "summary": "Test summary",
        "positioning": "Mid-range",
        "top_competitors": [],
        "recommendations": ["Lower price"],
    }

    db.save_analysis("B001234567", result)
    cached = db.get_cached_analysis("B001234567", max_age_minutes=60)

    assert cached is not None
    assert cached["summary"] == "Test summary"


def test_analysis_cache_returns_none_when_missing(tmp_path):
    db = Database(tmp_path / "data.json")
    assert db.get_cached_analysis("BNOTEXISTS") is None


def test_analysis_cache_expires(tmp_path):
    db = Database(tmp_path / "data.json")
    result = {"summary": "Old"}
    db.save_analysis("B001234567", result)

    # Force an old cached_at timestamp
    from tinydb import Query
    Analysis = Query()
    db.analyses.update({"cached_at": "2020-01-01T00:00:00"}, Analysis.asin == "B001234567")

    assert db.get_cached_analysis("B001234567", max_age_minutes=60) is None
