from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.scraper_client import extract_asin


class ScrapeRequest(BaseModel):
    asin: str | None = Field(None, min_length=5, max_length=300)
    product_url: str | None = Field(None, min_length=10, max_length=1000)
    domain: str = "com"
    country_code: str = Field("us", min_length=2, max_length=2)

    @model_validator(mode="after")
    def require_product_identifier(self):
        if not self.asin and not self.product_url:
            raise ValueError("Provide an Amazon product URL or ASIN.")
        return self

    def resolved_asin(self) -> str:
        return extract_asin(self.product_url or self.asin or "")


class ProductWorkflowRequest(ScrapeRequest):
    with_competitors: bool = True
    pages: int = Field(2, ge=1, le=5)


class CompetitorRequest(BaseModel):
    domain: str = "com"
    country_code: str = Field("us", min_length=2, max_length=2)
    pages: int = Field(2, ge=1, le=5)


class ProductResponse(BaseModel):
    asin: str
    title: str | None = None
    url: str | None = None
    brand: str | None = None
    price: float | str | None = None
    currency: str | None = None
    rating: float | str | None = None
    stock: str | None = None
    images: list[str] = Field(default_factory=list)
    categories: list[Any] = Field(default_factory=list)
    category_path: list[str] = Field(default_factory=list)
    amazon_domain: str | None = None
    country_code: str | None = None
    parent_asin: str | None = None
    scraped_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProductWorkflowResponse(BaseModel):
    product: ProductResponse
    competitors: list[ProductResponse] = Field(default_factory=list)
    competitors_found: int = 0


class PaginatedProducts(BaseModel):
    items: list[ProductResponse]
    page: int
    per_page: int
    total: int
    total_pages: int


class AnalysisResponse(BaseModel):
    asin: str
    summary: str
    positioning: str
    top_competitors: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class PriceHistoryPoint(BaseModel):
    asin: str
    price: float | str | None = None
    currency: str | None = None
    rating: float | str | None = None
    stock: str | None = None
    scraped_at: str


class PriceHistoryResponse(BaseModel):
    asin: str
    items: list[PriceHistoryPoint]
    total: int


class CompetitorListResponse(BaseModel):
    parent_asin: str
    items: list[ProductResponse]
    total: int


class JobCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    asin: str = Field(..., min_length=5, max_length=20)
    domain: str = "com"
    country_code: str = Field("us", min_length=2, max_length=2)
    with_competitors: bool = True
    pages: int = Field(2, ge=1, le=5)
    interval_minutes: int | None = Field(None, ge=15, le=10080)
    enabled: bool = True


class JobResponse(JobCreateRequest):
    id: int
    created_at: str
    updated_at: str | None = None
    last_run_at: str | None = None
    last_status: str | None = None


class JobRunResponse(BaseModel):
    id: int
    job_id: int | None = None
    status: Literal["success", "failed", "running"]
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    products_scraped: int = 0
    competitors_found: int = 0
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
