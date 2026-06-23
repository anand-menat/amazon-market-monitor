import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from src.automation import run_scrape_job, start_scheduler, stop_scheduler, sync_scheduler
from src.db import Database
from src.llm import analyze_competitors
from src.logging_config import configure_logging
from src.models import (
    AnalysisResponse,
    CompetitorListResponse,
    CompetitorRequest,
    JobCreateRequest,
    JobResponse,
    JobRunResponse,
    PaginatedProducts,
    PriceHistoryResponse,
    ProductResponse,
    ProductWorkflowRequest,
    ProductWorkflowResponse,
    ScrapeRequest,
)
from src.services import (
    fetch_and_store_competitors,
    get_stored_competitors,
    run_product_workflow,
    scrape_and_store_product,
)

configure_logging()

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _verify_api_key(key: str | None = Security(_API_KEY_HEADER)) -> None:
    """Enforce API key authentication when APP_API_KEY is configured."""
    required_key = os.getenv("APP_API_KEY")
    if not required_key:
        return  # Auth disabled in dev mode
    if key != required_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Amazon Competitor Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(_verify_api_key)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/products/scrape", response_model=ProductResponse)
def scrape_product(payload: ScrapeRequest):
    try:
        return scrape_and_store_product(payload.resolved_asin(), payload.country_code, payload.domain)
    except Exception as exc:
        if "404" in str(exc):
            raise HTTPException(status_code=404, detail="Product not found on Amazon.")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/products/workflow", response_model=ProductWorkflowResponse)
def scrape_product_workflow(payload: ProductWorkflowRequest):
    try:
        return run_product_workflow(
            asin=payload.resolved_asin(),
            country_code=payload.country_code,
            domain=payload.domain,
            with_competitors=payload.with_competitors,
            pages=payload.pages,
        )
    except Exception as exc:
        if "404" in str(exc):
            raise HTTPException(status_code=404, detail="Product not found on Amazon.")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/products", response_model=PaginatedProducts)
def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
):
    return Database().get_products_paginated(page=page, per_page=per_page)


@app.get("/api/products/{asin}", response_model=ProductResponse)
def get_product(asin: str):
    product = Database().get_product(asin)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/api/products/{asin}")
def delete_product(asin: str) -> dict[str, int]:
    db = Database()
    deleted = db.delete_product(asin)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"deleted": deleted}


@app.delete("/api/products")
def clear_all_products():
    db = Database()
    deleted = db.delete_all_products()
    return {"deleted": deleted}


@app.post("/api/products/{asin}/competitors", response_model=list[ProductResponse])
def fetch_competitors(asin: str, payload: CompetitorRequest):
    try:
        return fetch_and_store_competitors(
            parent_asin=asin,
            domain=payload.domain,
            country_code=payload.country_code,
            pages=payload.pages,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/products/{asin}/competitors", response_model=CompetitorListResponse)
def list_competitors(asin: str):
    items = get_stored_competitors(asin)
    return {"parent_asin": asin, "items": items, "total": len(items)}


@app.post("/api/products/{asin}/analyze", response_model=AnalysisResponse)
def analyze_product(asin: str):
    try:
        return {"asin": asin, **analyze_competitors(asin)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/products/{asin}/price-history", response_model=PriceHistoryResponse)
def get_price_history(asin: str, limit: int = Query(50, ge=1, le=200)):
    items = Database().get_price_history(asin, limit=limit)
    return {"asin": asin, "items": items, "total": len(items)}




@app.post("/api/jobs", response_model=JobResponse)
def create_job(payload: JobCreateRequest):
    db = Database()
    job_id = db.create_job(payload.model_dump())
    sync_scheduler()
    job = db.get_job(job_id)
    return {**job, "id": job_id}


@app.get("/api/jobs")
def list_jobs() -> dict:
    db = Database()
    return {
        "jobs": db.list_jobs(),
        "recent_runs": db.list_job_runs(limit=25),
    }


@app.post("/api/jobs/{job_id}/run", response_model=JobRunResponse)
def run_job(job_id: int):
    db = Database()
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return run_scrape_job(job, job_id=job_id)


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int) -> dict[str, bool]:
    deleted = Database().delete_job(job_id)
    sync_scheduler()
    return {"deleted": deleted}
