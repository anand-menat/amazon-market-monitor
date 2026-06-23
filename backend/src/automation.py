from datetime import datetime
import logging
from time import perf_counter
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from src.db import Database
from src.services import fetch_and_store_competitors, scrape_and_store_product


scheduler = BackgroundScheduler(timezone="UTC")
logger = logging.getLogger(__name__)


def run_scrape_job(job: dict[str, Any], job_id: int | None = None) -> dict[str, Any]:
    db = Database()
    started = datetime.now()
    timer = perf_counter()
    run = {
        "job_id": job_id,
        "status": "running",
        "started_at": started.isoformat(),
        "products_scraped": 0,
        "competitors_found": 0,
        "metadata": {
            "asin": job["asin"],
            "domain": job.get("domain", "com"),
            "country_code": job.get("country_code", "us"),
        },
    }
    logger.info("Starting scrape job job_id=%s asin=%s", job_id, job["asin"])

    try:
        scrape_and_store_product(
            asin=job["asin"],
            country_code=job.get("country_code", "us"),
            domain=job.get("domain", "com"),
        )
        run["products_scraped"] = 1

        if job.get("with_competitors", True):
            competitors = fetch_and_store_competitors(
                parent_asin=job["asin"],
                domain=job.get("domain", "com"),
                country_code=job.get("country_code", "us"),
                pages=job.get("pages", 2),
            )
            run["competitors_found"] = len(competitors)

        run["status"] = "success"
        logger.info(
            "Completed scrape job job_id=%s asin=%s competitors_found=%s",
            job_id,
            job["asin"],
            run["competitors_found"],
        )
    except Exception as exc:
        run["status"] = "failed"
        run["error"] = str(exc)
        logger.exception("Scrape job failed job_id=%s asin=%s", job_id, job.get("asin"))
    finally:
        finished = datetime.now()
        run["finished_at"] = finished.isoformat()
        run["duration_seconds"] = round(perf_counter() - timer, 2)
        run_id = db.insert_job_run(run)

        if job_id:
            db.update_job(
                job_id,
                {
                    "last_run_at": finished.isoformat(),
                    "last_status": run["status"],
                },
            )

    return {**run, "id": run_id}


def sync_scheduler() -> None:
    db = Database()
    for job in scheduler.get_jobs():
        job.remove()

    scheduled_count = 0
    for job in db.list_jobs():
        interval = job.get("interval_minutes")
        if not job.get("enabled", True) or not interval:
            continue

        scheduler.add_job(
            run_scrape_job,
            "interval",
            minutes=interval,
            args=[job, job["id"]],
            id=f"scrape-job-{job['id']}",
            replace_existing=True,
            max_instances=1,
        )
        scheduled_count += 1
    logger.info("Scheduler synced with %s enabled interval jobs", scheduled_count)


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
    sync_scheduler()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
