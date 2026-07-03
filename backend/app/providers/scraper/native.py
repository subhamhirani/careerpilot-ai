"""
CareerPilot AI — Native Scraper Provider
==========================================
Wraps the existing LinkedIn + Naukri scrapers behind the provider interface.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.providers.base import JobPosting, ScraperProvider

logger = logging.getLogger(__name__)


class NativeScraperProvider(ScraperProvider):
    """Uses the existing in-built LinkedIn and Naukri scrapers."""

    source_name = "native"

    def __init__(self) -> None:
        pass

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_pages_per_query: int = 1,
        **kwargs: Any,
    ) -> list[JobPosting]:
        """Run all native scrapers concurrently.

        Returns a flat deduplicated list of JobPosting objects.
        """
        from app.agents.multi_portal_scraper import (
            LinkedInGuestScraper,
            NaukriScraper,
            JobPosting as LegacyJobPosting,
            scrape_all as run_legacy_scrape,
        )

        linkedin_queries = kwargs.get("linkedin_queries") or queries
        naukri_queries = kwargs.get("naukri_queries") or queries

        if not linkedin_queries or not naukri_queries:
            raise ValueError("At least one query required for native scraper")

        # Use the existing unified scrape_all() which handles both sources
        # and deduplication internally.
        result = await run_legacy_scrape(
            linkedin_queries=linkedin_queries,
            naukri_queries=naukri_queries,
            location=location,
        )

        raw_jobs = result.get("jobs", [])
        return self._convert_jobs(raw_jobs)

    # ------------------------------------------------------------------
    #  Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_jobs(raw_jobs: list[dict | Any]) -> list[JobPosting]:
        """Convert legacy job dicts to provider-interface JobPosting objects."""
        results: list[JobPosting] = []
        seen_hashes: set[str] = set()
        for job in raw_jobs:
            if isinstance(job, dict):
                hk = job.get("hash_key", "") or ""
                if hk and hk in seen_hashes:
                    continue
                if hk:
                    seen_hashes.add(hk)
                results.append(
                    JobPosting(
                        source=job.get("source", ""),
                        source_job_id=job.get("source_job_id", ""),
                        title=job.get("title", ""),
                        company=job.get("company", ""),
                        location=job.get("location", ""),
                        description=job.get("description", ""),
                        url=job.get("url", ""),
                        posted_at=job.get("posted_at", ""),
                        salary=job.get("salary", ""),
                        employment_type=job.get("employment_type", ""),
                        work_mode=job.get("work_mode", ""),
                        skills=job.get("skills", []),
                        experience_required=job.get("experience_required", ""),
                        hash_key=hk,
                        scraped_at=job.get("scraped_at", ""),
                    )
                )
            else:
                # Legacy JobPosting dataclass instance
                hk = getattr(job, "hash_key", "") or ""
                if hk and hk in seen_hashes:
                    continue
                if hk:
                    seen_hashes.add(hk)
                results.append(
                    JobPosting(
                        source=getattr(job, "source", ""),
                        source_job_id=getattr(job, "source_job_id", ""),
                        title=getattr(job, "title", ""),
                        company=getattr(job, "company", ""),
                        location=getattr(job, "location", ""),
                        description=getattr(job, "description", ""),
                        url=getattr(job, "url", ""),
                        posted_at=getattr(job, "posted_at", ""),
                        salary=getattr(job, "salary", ""),
                        employment_type=getattr(job, "employment_type", ""),
                        work_mode=getattr(job, "work_mode", ""),
                        skills=getattr(job, "skills", []),
                        experience_required=getattr(job, "experience_required", ""),
                        hash_key=hk,
                        scraped_at=getattr(job, "scraped_at", ""),
                    )
                )
        return results
