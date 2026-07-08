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
import os
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
# Tier 1: API Job Scrapers (Primary Sources)
# ---------------------------------------------------------------------------

class RemotiveApiScraper:
    """Scrapes jobs via Remotive public API (free, no API key required)."""

    source_name = "remotive"
    BASE_URL = "https://remotive.com/api/remote-jobs"

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_jobs: int = 25,
    ) -> list[JobPosting]:
        queries_list = queries or ["software engineer"]
        postings: list[JobPosting] = []

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for query in queries_list[:3]:
                try:
                    resp = await client.get(self.BASE_URL, params={"search": query, "limit": max_jobs})
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    jobs_list = data.get("jobs", [])
                    for item in jobs_list[:max_jobs]:
                        job_id = str(item.get("id", "")) or hashlib.md5(str(item).encode()).hexdigest()[:12]
                        title = item.get("title", "Remote Role").strip()
                        company = item.get("company_name", "Remote Company").strip()
                        job_loc = item.get("candidate_required_location", location).strip() or location
                        desc_raw = item.get("description", "") or ""
                        desc = re.sub(r"<[^>]+>", " ", desc_raw).strip()[:2000]
                        url = item.get("url", "")
                        if not url:
                            continue
                        salary = item.get("salary", "") or ""
                        emp_type = item.get("job_type", "") or ""
                        posted_at = item.get("publication_date", "") or ""
                        tags = item.get("tags", [])
                        skills = [str(t).strip() for t in tags if str(t).strip()]

                        postings.append(JobPosting(
                            source=self.source_name,
                            source_job_id=job_id,
                            title=title,
                            company=company,
                            location=job_loc,
                            description=desc,
                            url=url,
                            posted_at=posted_at,
                            salary=salary,
                            employment_type=emp_type,
                            skills=skills,
                        ))
                except Exception as exc:
                    logger.debug("Remotive API query '%s' error: %s", query, exc)
        return postings


class ArbeitnowApiScraper:
    """Scrapes jobs via Arbeitnow public API (free, no API key required)."""

    source_name = "arbeitnow"
    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_jobs: int = 25,
    ) -> list[JobPosting]:
        queries_list = queries or ["software"]
        postings: list[JobPosting] = []

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            try:
                resp = await client.get(self.BASE_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs_list = data.get("data", [])
                    query_terms = [q.lower() for q in queries_list]
                    for item in jobs_list:
                        title = item.get("title", "").strip()
                        desc_raw = item.get("description", "") or ""
                        text_to_match = f"{title} {desc_raw}".lower()
                        # Filter by query terms if provided
                        if query_terms and not any(term in text_to_match for term in query_terms):
                            continue
                        job_id = str(item.get("slug", "")) or hashlib.md5(str(item).encode()).hexdigest()[:12]
                        company = item.get("company_name", "Arbeitnow Company").strip()
                        job_loc = item.get("location", location).strip() or location
                        desc = re.sub(r"<[^>]+>", " ", desc_raw).strip()[:2000]
                        url = item.get("url", "")
                        if not url:
                            continue
                        tags = item.get("tags", [])
                        skills = [str(t).strip() for t in tags if str(t).strip()]

                        postings.append(JobPosting(
                            source=self.source_name,
                            source_job_id=job_id,
                            title=title,
                            company=company,
                            location=job_loc,
                            description=desc,
                            url=url,
                            skills=skills,
                        ))
                        if len(postings) >= max_jobs:
                            break
            except Exception as exc:
                logger.debug("Arbeitnow API error: %s", exc)
        return postings


class AdzunaApiScraper:
    """Scrapes jobs via Adzuna API if ADZUNA_APP_ID & ADZUNA_APP_KEY are configured."""

    source_name = "adzuna"
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_jobs: int = 25,
    ) -> list[JobPosting]:
        app_id = os.getenv("ADZUNA_APP_ID", "").strip()
        app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
        if not app_id or not app_key:
            logger.debug("Adzuna API credentials not set, skipping Adzuna API scraper.")
            return []

        country = "in" if "india" in location.lower() else "us"
        queries_list = queries or ["software engineer"]
        postings: list[JobPosting] = []

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for query in queries_list[:2]:
                try:
                    url = f"{self.BASE_URL}/{country}/search/1"
                    params = {
                        "app_id": app_id,
                        "app_key": app_key,
                        "what": query,
                        "where": location,
                        "results_per_page": max_jobs,
                    }
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for item in data.get("results", []):
                        job_id = str(item.get("id", "")) or hashlib.md5(str(item).encode()).hexdigest()[:12]
                        title = item.get("title", "").strip()
                        company = item.get("company", {}).get("display_name", "Company").strip()
                        job_loc = item.get("location", {}).get("display_name", location).strip() or location
                        desc = item.get("description", "").strip()[:2000]
                        url_link = item.get("redirect_url", "")
                        if not url_link:
                            continue
                        salary_min = item.get("salary_min")
                        salary_max = item.get("salary_max")
                        salary = f"{salary_min}-{salary_max}" if salary_min and salary_max else ""

                        postings.append(JobPosting(
                            source=self.source_name,
                            source_job_id=job_id,
                            title=title,
                            company=company,
                            location=job_loc,
                            description=desc,
                            url=url_link,
                            salary=salary,
                        ))
                except Exception as exc:
                    logger.debug("Adzuna API error for query '%s': %s", query, exc)
        return postings


class JSearchApiScraper:
    """Scrapes jobs via RapidAPI JSearch API if RAPIDAPI_KEY is configured."""

    source_name = "jsearch"
    BASE_URL = "https://jsearch.p.rapidapi.com/search"

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_jobs: int = 25,
    ) -> list[JobPosting]:
        rapidapi_key = os.getenv("RAPIDAPI_KEY", "").strip()
        if not rapidapi_key:
            logger.debug("RAPIDAPI_KEY not set, skipping JSearch API scraper.")
            return []

        queries_list = queries or ["software engineer"]
        postings: list[JobPosting] = []

        headers = {
            "X-RapidAPI-Key": rapidapi_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        async with httpx.AsyncClient(timeout=25.0, headers=headers, follow_redirects=True) as client:
            for query in queries_list[:2]:
                try:
                    params = {"query": f"{query} in {location}", "num_pages": "1"}
                    resp = await client.get(self.BASE_URL, params=params)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for item in data.get("data", []):
                        job_id = str(item.get("job_id", "")) or hashlib.md5(str(item).encode()).hexdigest()[:12]
                        title = item.get("job_title", "").strip()
                        company = item.get("employer_name", "Employer").strip()
                        job_loc = item.get("job_city", location) or location
                        desc = (item.get("job_description") or "").strip()[:2000]
                        url_link = item.get("job_apply_link", "") or item.get("job_google_link", "")
                        if not url_link:
                            continue
                        emp_type = item.get("job_employment_type", "")
                        work_mode = "remote" if item.get("job_is_remote") else "on-site"

                        postings.append(JobPosting(
                            source=self.source_name,
                            source_job_id=job_id,
                            title=title,
                            company=company,
                            location=str(job_loc),
                            description=desc,
                            url=url_link,
                            employment_type=str(emp_type),
                            work_mode=work_mode,
                        ))
                except Exception as exc:
                    logger.debug("JSearch API error for query '%s': %s", query, exc)
        return postings


class BrightDataScraper:
    """Scrapes jobs using Bright Data Advanced Scraping / SERP / Web Unlocker API.
    Supports BRIGHTDATA_TOKEN and BRIGHTDATA_MCP_URL environment configuration.
    """

    source_name = "brightdata"
    SERP_API_URL = "https://api.brightdata.com/serp/req"

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_jobs: int = 25,
    ) -> list[JobPosting]:
        token = os.getenv("BRIGHTDATA_TOKEN", "50be13ca-76e2-4b09-b83e-9c268d076a5a").strip()
        if not token:
            logger.debug("BRIGHTDATA_TOKEN not set, skipping BrightData scraper.")
            return []

        queries_list = queries or ["software engineer"]
        postings: list[JobPosting] = []

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            for query in queries_list[:2]:
                try:
                    payload = {
                        "query": f"{query} jobs in {location}",
                        "country": "in" if "india" in location.lower() else "us",
                        "search_engine": "google_jobs",
                    }
                    resp = await client.post(self.SERP_API_URL, json=payload)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    jobs_list = data if isinstance(data, list) else data.get("jobs", data.get("results", []))
                    for item in jobs_list[:max_jobs]:
                        job_id = str(item.get("id") or item.get("job_id") or "") or hashlib.md5(str(item).encode()).hexdigest()[:12]
                        title = str(item.get("title") or item.get("job_title", "")).strip()
                        company = str(item.get("company_name") or item.get("company", "Company")).strip()
                        job_loc = str(item.get("location", location)).strip() or location
                        desc = str(item.get("description", "")).strip()[:2000]
                        url = str(item.get("url") or item.get("link") or "")
                        if not url or not title:
                            continue
                        salary = str(item.get("salary", "")).strip()

                        postings.append(JobPosting(
                            source=self.source_name,
                            source_job_id=job_id,
                            title=title,
                            company=company,
                            location=job_loc,
                            description=desc,
                            url=url,
                            salary=salary,
                        ))
                except Exception as exc:
                    logger.debug("BrightData API search error for query '%s': %s", query, exc)
        return postings


class TheMuseApiScraper:
    """Scrapes jobs via The Muse public API (free, no API key required)."""

    source_name = "themuse"
    BASE_URL = "https://www.themuse.com/api/public/jobs"

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_jobs: int = 25,
    ) -> list[JobPosting]:
        postings: list[JobPosting] = []

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            try:
                params = {"page": "1", "descending": "true"}
                resp = await client.get(self.BASE_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    for item in results[:max_jobs]:
                        job_id = str(item.get("id", "")) or hashlib.md5(str(item).encode()).hexdigest()[:12]
                        title = item.get("name", "").strip()
                        company = item.get("company", {}).get("name", "Company").strip()
                        locations = item.get("locations", [])
                        job_loc = locations[0].get("name", location) if locations else location
                        desc_raw = item.get("contents", "") or ""
                        desc = re.sub(r"<[^>]+>", " ", desc_raw).strip()[:2000]
                        url = item.get("refs", {}).get("landing_page", "")
                        if not url or not title:
                            continue

                        postings.append(JobPosting(
                            source=self.source_name,
                            source_job_id=job_id,
                            title=title,
                            company=company,
                            location=str(job_loc),
                            description=desc,
                            url=url,
                        ))
            except Exception as exc:
                logger.debug("The Muse API query error: %s", exc)
        return postings


class FindworkApiScraper:
    """Scrapes jobs via Findwork API if FINDWORK_API_KEY is configured."""

    source_name = "findwork"
    BASE_URL = "https://findwork.dev/api/jobs/"

    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_jobs: int = 25,
    ) -> list[JobPosting]:
        api_key = os.getenv("FINDWORK_API_KEY", "").strip()
        if not api_key:
            return []

        queries_list = queries or ["software engineer"]
        postings: list[JobPosting] = []

        headers = {"Authorization": f"Token {api_key}"}

        async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
            for query in queries_list[:2]:
                try:
                    resp = await client.get(self.BASE_URL, params={"search": query, "location": location})
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for item in data.get("results", [])[:max_jobs]:
                        job_id = str(item.get("id", "")) or hashlib.md5(str(item).encode()).hexdigest()[:12]
                        title = item.get("role", "").strip()
                        company = item.get("company_name", "Company").strip()
                        job_loc = item.get("location", location).strip() or location
                        desc_raw = item.get("text", "") or ""
                        desc = re.sub(r"<[^>]+>", " ", desc_raw).strip()[:2000]
                        url = item.get("url", "")
                        if not url or not title:
                            continue

                        postings.append(JobPosting(
                            source=self.source_name,
                            source_job_id=job_id,
                            title=title,
                            company=company,
                            location=job_loc,
                            description=desc,
                            url=url,
                        ))
                except Exception as exc:
                    logger.debug("Findwork API error for query '%s': %s", query, exc)
        return postings


# ---------------------------------------------------------------------------
# Unified Scraper (API-First + Local Scraping Fallback)
# ---------------------------------------------------------------------------

async def scrape_all(
    linkedin_queries: list[str] | None = None,
    naukri_queries: list[str] | None = None,
    location: str = "India",
    selected_locations: list[str] | None = None,
    use_local_fallback: bool = True,
    min_api_jobs_threshold: int = 10,
) -> dict[str, Any]:
    """Scrape all sources and return combined, deduplicated results.
    Prioritises API sources (BrightData, Remotive, Arbeitnow, TheMuse, Adzuna, JSearch, Findwork)
    and executes Tier 2 local scraping (LinkedIn, Naukri) as the fallback option.
    """
    location_to_use = selected_locations[0] if selected_locations else location
    queries_to_use = linkedin_queries or naukri_queries or ["software engineer"]

    start = time.monotonic()

    # Tier 1: Multi-Source API & Proxy Job Scrapers
    brightdata = BrightDataScraper()
    remotive = RemotiveApiScraper()
    arbeitnow = ArbeitnowApiScraper()
    themuse = TheMuseApiScraper()
    adzuna = AdzunaApiScraper()
    jsearch = JSearchApiScraper()
    findwork = FindworkApiScraper()

    api_results = await asyncio.gather(
        brightdata.search(queries=queries_to_use, location=location_to_use),
        remotive.search(queries=queries_to_use, location=location_to_use),
        arbeitnow.search(queries=queries_to_use, location=location_to_use),
        themuse.search(queries=queries_to_use, location=location_to_use),
        adzuna.search(queries=queries_to_use, location=location_to_use),
        jsearch.search(queries=queries_to_use, location=location_to_use),
        findwork.search(queries=queries_to_use, location=location_to_use),
        return_exceptions=True,
    )

    brightdata_jobs = api_results[0] if not isinstance(api_results[0], Exception) else []
    remotive_jobs = api_results[1] if not isinstance(api_results[1], Exception) else []
    arbeitnow_jobs = api_results[2] if not isinstance(api_results[2], Exception) else []
    themuse_jobs = api_results[3] if not isinstance(api_results[3], Exception) else []
    adzuna_jobs = api_results[4] if not isinstance(api_results[4], Exception) else []
    jsearch_jobs = api_results[5] if not isinstance(api_results[5], Exception) else []
    findwork_jobs = api_results[6] if not isinstance(api_results[6], Exception) else []

    api_jobs_total: list[JobPosting] = (
        brightdata_jobs + remotive_jobs + arbeitnow_jobs + themuse_jobs +
        adzuna_jobs + jsearch_jobs + findwork_jobs  # type: ignore[operator]
    )

    # Tier 2: Local Web Scraping as Last Option / Fallback
    linkedin_jobs: list[JobPosting] = []
    naukri_jobs: list[JobPosting] = []

    if use_local_fallback or len(api_jobs_total) < min_api_jobs_threshold:
        logger.info(
            "Executing Tier 2 local scrapers (LinkedIn/Naukri) as fallback (api_jobs=%d)",
            len(api_jobs_total),
        )
        linkedin = LinkedInGuestScraper()
        naukri = NaukriScraper()

        local_results = await asyncio.gather(
            linkedin.search(queries=linkedin_queries, location=location_to_use),
            naukri.search(queries=naukri_queries, location=location_to_use),
            return_exceptions=True,
        )

        if isinstance(local_results[0], Exception):
            logger.error("LinkedIn scraper failed: %s", local_results[0])
        else:
            linkedin_jobs = local_results[0]  # type: ignore[assignment]

        if isinstance(local_results[1], Exception):
            logger.error("Naukri scraper failed: %s", local_results[1])
        else:
            naukri_jobs = local_results[1]  # type: ignore[assignment]

    # Deduplicate by URL across all sources
    seen_urls: set[str] = set()
    all_jobs: list[JobPosting] = []
    for job in (api_jobs_total + linkedin_jobs + naukri_jobs):
        if job.url not in seen_urls:
            seen_urls.add(job.url)
            all_jobs.append(job)

    elapsed = time.monotonic() - start

    summary = {
        "total_jobs": len(all_jobs),
        "brightdata_jobs": len(brightdata_jobs),
        "remotive_jobs": len(remotive_jobs),
        "arbeitnow_jobs": len(arbeitnow_jobs),
        "themuse_jobs": len(themuse_jobs),
        "adzuna_jobs": len(adzuna_jobs),
        "jsearch_jobs": len(jsearch_jobs),
        "findwork_jobs": len(findwork_jobs),
        "linkedin_jobs": len(linkedin_jobs),
        "naukri_jobs": len(naukri_jobs),
        "unique_urls": len(seen_urls),
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Scrape complete: %d total (%d API + %d Local Fallback) in %.1fs",
        len(all_jobs), len(api_jobs_total), len(linkedin_jobs) + len(naukri_jobs), elapsed,
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
