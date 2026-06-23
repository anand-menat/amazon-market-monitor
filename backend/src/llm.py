import json
import logging
import os
from typing import Optional

from pydantic import BaseModel, Field

from src.db import Database


class CompetitorInsights(BaseModel):
    asin: str
    title: Optional[str]
    price: Optional[float | str]
    currency: Optional[str]
    rating: Optional[float | str]
    key_points: list[str] = Field(default_factory=list)


class AnalysisOutput(BaseModel):
    summary: str
    positioning: str
    top_competitors: list[CompetitorInsights]
    recommendations: list[str]


def format_competitors(db: Database, parent_asin: str) -> list[dict]:
    comps = db.search_products({"parent_asin": parent_asin})
    return [
        {
            "asin": c.get("asin"),
            "title": c.get("title"),
            "price": c.get("price"),
            "currency": c.get("currency"),
            "rating": c.get("rating"),
            "amazon_domain": c.get("amazon_domain"),
        }
        for c in comps
    ]


logger = logging.getLogger(__name__)


def analyze_competitors(asin: str) -> dict:
    db = Database()

    # Return cached result if fresh
    cached = db.get_cached_analysis(asin, max_age_minutes=60)
    if cached:
        logger.info("Returning cached analysis for asin=%s", asin)
        return {
            "summary": cached.get("summary", ""),
            "positioning": cached.get("positioning", ""),
            "top_competitors": cached.get("top_competitors", []),
            "recommendations": cached.get("recommendations", []),
        }

    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing. Add it to backend/.env to use analysis.")

    from openai import OpenAI

    db = Database()
    product = db.get_product(asin)
    competitors = format_competitors(db, asin)

    prompt = (
        "You are a market analyst reviewing Amazon competitor data for an automation dashboard.\n"
        "Write concise, practical recommendations. Keep currency context accurate.\n\n"
        "Return only valid JSON with this exact shape:\n"
        "{\n"
        '  "summary": "string",\n'
        '  "positioning": "string",\n'
        '  "top_competitors": [\n'
        '    {"asin": "string", "title": "string", "price": 0, "currency": "string", "rating": 0, "key_points": ["string"]}\n'
        "  ],\n"
        '  "recommendations": ["string"]\n'
        "}\n\n"
        f"Product JSON: {json.dumps(product or {'asin': asin}, default=str)}\n\n"
        f"Competitors JSON: {json.dumps(competitors, default=str)}"
    )

    client = OpenAI(
        api_key=deepseek_api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        messages=[
            {"role": "system", "content": "You return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    raw_content = response.choices[0].message.content or "{}"
    cleaned_content = raw_content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    result = AnalysisOutput.model_validate(json.loads(cleaned_content))
    result_dict = result.model_dump()

    # Cache the result
    db.save_analysis(asin, result_dict)
    logger.info("Cached new analysis for asin=%s", asin)

    return result_dict
