"""
CareerPilot AI — Unified Multi-Portal Job Scraper
===================================================
Scrapes job listings from multiple public sources using their guest APIs.
No API keys required. Designed for production use with real resume data.

Sources:
  - LinkedIn Guest API (public job search, no auth)
  - Naukri Public API (guest search endpoint)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class JobPosting:
    """Normalised job posting from any source."""
    source: str
    source_job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_at: str = ""
    salary: str = ""
    employment_type: str = ""
    work_mode: str = ""
    skills: list[str] = field(default_factory=list)
    experience_required: str = ""
    hash_key: str = ""
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now(timezone.utc).isoformat()
        if not self.hash_key:
            unique_str = f"{self.source}|{self.source_job_id}|{self.title}|{self.company}"
            self.hash_key = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Simple async rate limiter."""

    def __init__(self, delay: float = 1.0):
        self._delay = delay
        self._last: float = 0

    async def acquire(self):
        now = time.monotonic()
        wait = self._delay - (now - self._last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.monotonic()


# ---------------------------------------------------------------------------
# LinkedIn Guest Scraper
# ---------------------------------------------------------------------------

class LinkedInGuestScraper:
    """Scrapes LinkedIn public job search (no authentication required).

    Uses the LinkedIn guest/public job search endpoint which returns
    server-rendered HTML with full job card data.
    """

    source_name = "linkedin"
    BASE_URL = "https://www.linkedin.com/jobs/search"

    # Search queries to maximise coverage
    DEFAULT_QUERIES = [
        "software engineer",
        "software developer",
        "python developer",
        "backend engineer",
        "full stack developer",
        "devops engineer",
        "network engineer",
        "infrastructure engineer",
        "cloud engineer",
        "cybersecurity analyst",
        "SOC analyst",
        "security analyst",
        "system administrator",
        "Windows administrator",
        "Linux administrator",
        "Docker",
        "AWS",
    ]

    def __init__(self, rate_limiter: RateLimiter | None = None):
        self.rate_limiter = rate_limiter or RateLimiter(delay=1.5)

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_pages_per_query: int = 1,
    ) -> list[JobPosting]:
        """Scrape LinkedIn guest jobs for multiple queries."""
        queries = queries or self.DEFAULT_QUERIES
        all_jobs: list[JobPosting] = []
        seen_urls: set[str] = set()

        client = await self._client()

        for query in queries:
            for page in range(max_pages_per_query):
                start = page * 25
                params = {
                    "keywords": query,
                    "location": location,
                    "f_TPR": "r2592000",  # last 30 days
                    "f_E": "1",  # entry level
                    "sortBy": "DD",
                }
                if start > 0:
                    params["start"] = str(start)

                url = f"{self.BASE_URL}?{urlencode(params)}"

                await self.rate_limiter.acquire()
                logger.info("LinkedIn [%s] page %d: %s", query, page + 1, url)

                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.warning("LinkedIn HTTP error: %s", exc)
                    continue

                soup = self._soup(resp.text)
                cards = soup.select("div.base-card")

                if not cards:
                    logger.info("LinkedIn [%s] page %d: no cards", query, page + 1)
                    break

                new_count = 0
                for card in cards:
                    job = self._parse_card(card)
                    if job and job.url not in seen_urls:
                        seen_urls.add(job.url)
                        all_jobs.append(job)
                        new_count += 1

                logger.info(
                    "LinkedIn [%s] page %d: %d cards, %d new",
                    query, page + 1, len(cards), new_count,
                )

                await asyncio.sleep(1.0)

        await self._close(client)
        logger.info("LinkedIn total: %d unique jobs", len(all_jobs))
        return all_jobs

    def _parse_card(self, card: BeautifulSoup) -> JobPosting | None:
        """Extract a JobPosting from a LinkedIn job card."""
        # URL
        link_el = card.select_one("a.base-card__full-link")
        if not link_el:
            link_el = card.select_one("a.job-card-list__title")
        if not link_el:
            return None

        url = link_el.get("href", "")
        if not url:
            return None

        # Source job ID from URL
        match = re.search(r"/jobs/view/([^?]+)", url)
        source_job_id = match.group(1) if match else hashlib.md5(url.encode()).hexdigest()[:12]

        # Title
        title_el = card.select_one("h3.base-search-card__title")
        if not title_el:
            title_el = card.select_one("a.job-card-list__title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        # Company
        company_el = card.select_one("h4.base-search-card__subtitle")
        if not company_el:
            company_el = card.select_one("span.job-card-container__primary-description")
        company = company_el.get_text(strip=True) if company_el else ""

        # Location
        loc_el = card.select_one("span.job-search-card__location")
        if not loc_el:
            loc_el = card.select_one("span.job-card-container__metadata-item")
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Posted time
        time_el = card.select_one("time")
        posted_at = time_el.get_text(strip=True) if time_el else ""

        return JobPosting(
            source=self.source_name,
            source_job_id=source_job_id,
            title=title,
            company=company,
            location=location,
            description="",
            url=url,
            posted_at=posted_at,
        )

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
            },
            timeout=httpx.Timeout(30.0, connect=15.0),
            follow_redirects=True,
        )

    async def _close(self, client: httpx.AsyncClient):
        await client.aclose()

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# Naukri Public API Scraper
# ---------------------------------------------------------------------------

class NaukriScraper:
    """Scrapes Naukri.com via their public search API."""

    source_name = "naukri"
    API_URL = "https://www.naukri.com/jobapi/v1/search"

    DEFAULT_QUERIES = [
        "software engineer",
        "software developer",
        "python developer",
        "backend engineer",
        "full stack developer",
        "devops engineer",
        "network engineer",
        "infrastructure engineer",
        "cloud engineer",
        "cybersecurity",
        "system administrator",
        "Windows administrator",
        "Linux administrator",
        "Docker",
        "AWS",
    ]

    def __init__(self, rate_limiter: RateLimiter | None = None):
        self.rate_limiter = rate_limiter or RateLimiter(delay=1.0)

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_pages_per_query: int = 1,
    ) -> list[JobPosting]:
        """Scrape Naukri jobs for multiple queries."""
        queries = queries or self.DEFAULT_QUERIES
        all_jobs: list[JobPosting] = []
        seen_ids: set[str] = set()

        client = await self._client()

        for query in queries:
            for page in range(1, max_pages_per_query + 1):
                params = {
                    "query": query,
                    "location": location,
                    "pageNo": page,
                    "pageSize": 20,
                }
                url = f"{self.API_URL}?{urlencode(params)}"

                await self.rate_limiter.acquire()
                logger.info("Naukri [%s] page %d", query, page)

                try:
                    resp = await client.get(
                        url,
                        headers={
                            "Accept": "application/json",
                            "Referer": "https://www.naukri.com/",
                        },
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.warning("Naukri HTTP error: %s", exc)
                    continue

                try:
                    data = resp.json()
                except Exception:
                    logger.warning("Naukri returned non-JSON")
                    continue

                items = data.get("list", [])
                if not items:
                    break

                new_count = 0
                for item in items:
                    job = self._parse_item(item)
                    if job and job.source_job_id not in seen_ids:
                        seen_ids.add(job.source_job_id)
                        all_jobs.append(job)
                        new_count += 1

                logger.info(
                    "Naukri [%s] page %d: %d items, %d new",
                    query, page, len(items), new_count,
                )

                await asyncio.sleep(1.0)

        await self._close(client)
        logger.info("Naukri total: %d unique jobs", len(all_jobs))
        return all_jobs

    @staticmethod
    def _parse_item(item: dict) -> JobPosting | None:
        """Convert a Naukri API job dict to a JobPosting."""
        title = item.get("post", "") or item.get("tupleDesc", "")
        if not title:
            return None

        title = re.sub(r"<[^>]+>", "", title).strip()
        if not title:
            return None

        company = item.get("companyName", "") or item.get("CONTCOM", "")
        location = item.get("cityfield", "")
        location = re.sub(r"\s+", " ", location).strip()

        # Salary
        min_sal = item.get("minSal", 0) or 0
        max_sal = item.get("maxSal", 0) or 0
        try:
            min_sal = float(min_sal)
        except (ValueError, TypeError):
            min_sal = 0
        try:
            max_sal = float(max_sal)
        except (ValueError, TypeError):
            max_sal = 0
        currency = item.get("currencySal", "INR")
        salary = ""
        if min_sal > 0 and max_sal > 0:
            salary = f"{currency} {int(min_sal)} - {int(max_sal)}"
        elif min_sal > 0:
            salary = f"{currency} {int(min_sal)}+"

        # Experience
        min_exp = item.get("minExp", 0) or 0
        max_exp = item.get("maxExp", 0) or 0
        try:
            min_exp = float(min_exp)
        except (ValueError, TypeError):
            min_exp = 0
        try:
            max_exp = float(max_exp)
        except (ValueError, TypeError):
            max_exp = 0
        experience = ""
        if min_exp > 0 and max_exp > 0:
            experience = f"{int(min_exp)}-{int(max_exp)} years"
        elif min_exp > 0:
            experience = f"{int(min_exp)}+ years"

        employment_type = item.get("employmentType", "")

        job_desc = item.get("jobDesc", "") or ""
        description = re.sub(r"<[^>]+>", " ", job_desc).strip()[:2000] if job_desc else ""

        url = item.get("urlStr", "") or item.get("nonStaticUrlFor", "")
        if url and not url.startswith("http"):
            url = urljoin("https://www.naukri.com", url)

        source_job_id = str(item.get("jobId", "")) or hashlib.md5(url.encode()).hexdigest()[:12]

        keywords_raw = item.get("keywords", "")
        skills = [k.strip() for k in keywords_raw.split(",") if k.strip()] if keywords_raw else []

        return JobPosting(
            source="naukri",
            source_job_id=source_job_id,
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            salary=salary,
            employment_type=employment_type,
            skills=skills,
            experience_required=experience,
        )

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-IN,en;q=0.9",
            },
            timeout=httpx.Timeout(30.0, connect=15.0),
            follow_redirects=True,
        )

    async def _close(self, client: httpx.AsyncClient):
        await client.aclose()


# ---------------------------------------------------------------------------
# Unified Scraper
# ---------------------------------------------------------------------------

async def scrape_all(
    linkedin_queries: list[str] | None = None,
    naukri_queries: list[str] | None = None,
    location: str = "India",
) -> dict[str, Any]:
    """Scrape all sources and return combined, deduplicated results."""
    start = time.monotonic()

    linkedin = LinkedInGuestScraper()
    naukri = NaukriScraper()

    # Run both sources concurrently
    results = await asyncio.gather(
        linkedin.search(queries=linkedin_queries, location=location),
        naukri.search(queries=naukri_queries, location=location),
        return_exceptions=True,
    )

    linkedin_jobs: list[JobPosting] = []
    naukri_jobs: list[JobPosting] = []

    if isinstance(results[0], Exception):
        logger.error("LinkedIn scraper failed: %s", results[0])
    else:
        linkedin_jobs = results[0]  # type: ignore[assignment]

    if isinstance(results[1], Exception):
        logger.error("Naukri scraper failed: %s", results[1])
    else:
        naukri_jobs = results[1]  # type: ignore[assignment]

    # Deduplicate by URL
    seen_urls: set[str] = set()
    all_jobs: list[JobPosting] = []
    for job in linkedin_jobs + naukri_jobs:
        if job.url not in seen_urls:
            seen_urls.add(job.url)
            all_jobs.append(job)

    elapsed = time.monotonic() - start

    summary = {
        "total_jobs": len(all_jobs),
        "linkedin_jobs": len(linkedin_jobs),
        "naukri_jobs": len(naukri_jobs),
        "unique_urls": len(seen_urls),
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Scrape complete: %d total (%d LinkedIn + %d Naukri) in %.1fs",
        len(all_jobs), len(linkedin_jobs), len(naukri_jobs), elapsed,
    )

    return {"summary": summary, "jobs": [asdict(j) for j in all_jobs]}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    result = asyncio.run(scrape_all())
    summary = result["summary"]
    jobs = result["jobs"]

    print()
    print("=" * 60)
    print("  MULTI-PORTAL JOB SCRAPE RESULTS")
    print("=" * 60)
    print(f"  Total unique jobs : {summary['total_jobs']}")
    print(f"  LinkedIn jobs     : {summary['linkedin_jobs']}")
    print(f"  Naukri jobs       : {summary['naukri_jobs']}")
    print(f"  Time elapsed      : {summary['elapsed_seconds']}s")
    print(f"  Timestamp         : {summary['timestamp']}")
    print("=" * 60)
    print()

    for i, job in enumerate(jobs[:20]):
        print(f"{i+1:3d}. {job['title']}")
        print(f"     @ {job['company']} | {job['location']}")
        if job.get('salary'):
            print(f"     Salary: {job['salary']}")
        if job.get('experience_required'):
            print(f"     Experience: {job['experience_required']}")
        print(f"     Source: {job['source']} | {job['url'][:80]}")
        print()

    if len(jobs) > 20:
        print(f"... and {len(jobs) - 20} more jobs")

    # Save full results
    output_path = "/tmp/scrape_results.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to: {output_path}")
