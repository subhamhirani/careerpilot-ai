"""
CareerPilot AI — API-based Scraper Provider
=============================================
Uses an external HTTP API to search for jobs.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.providers.base import JobPosting, ScraperProvider

logger = logging.getLogger(__name__)


class ApiScraperProvider(ScraperProvider):
    """Sends search requests to an external job-scraping API."""

    source_name = "api"

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_url = (api_url or os.getenv("SCRAPER_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("SCRAPER_API_KEY", "")
        self.timeout = timeout

        if not self.api_url:
            raise ValueError(
                "SCRAPER_API_URL is required for ApiScraperProvider. "
                "Set it via env var or the constructor."
            )

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_pages_per_query: int = 1,
        **kwargs: Any,
    ) -> list[JobPosting]:
        """POST queries to the external scraper API."""
        payload: dict[str, Any] = {
            "queries": queries or [],
            "location": location,
            "max_pages_per_query": max_pages_per_query,
        }
        # Forward any extra kwargs (source-specific filters, etc.)
        payload.update(kwargs)

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
        ) as client:
            logger.info(
                "API Scraper -> POST %s (queries=%s, location=%s)",
                self.api_url,
                queries,
                location,
            )
            resp = await client.post(
                f"{self.api_url}/jobs/search",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        raw_jobs: list[dict] = data.get("jobs", data.get("results", data.get("data", [])))
        if isinstance(raw_jobs, dict):
            raw_jobs = [raw_jobs]

        return self._parse_response(raw_jobs)

    # ------------------------------------------------------------------
    #  Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw_jobs: list[dict]) -> list[JobPosting]:
        """Convert API response dicts into JobPosting objects."""
        results: list[JobPosting] = []
        for item in raw_jobs:
            results.append(
                JobPosting(
                    source=item.get("source", "api"),
                    source_job_id=str(item.get("source_job_id", item.get("id", ""))),
                    title=item.get("title", ""),
                    company=item.get("company", ""),
                    location=item.get("location", ""),
                    description=item.get("description", ""),
                    url=item.get("url", item.get("apply_url", "")),
                    posted_at=item.get("posted_at", item.get("date", "")),
                    salary=item.get("salary", ""),
                    employment_type=item.get("employment_type", ""),
                    work_mode=item.get("work_mode", ""),
                    skills=item.get("skills", []),
                    experience_required=item.get("experience_required", ""),
                    hash_key=item.get("hash_key", ""),
                    scraped_at=item.get("scraped_at", ""),
                )
            )
        return results
