"""
CareerPilot AI — Agent 2: Job Discovery Agent
==============================================
Scrapes job listings from multiple Indian job boards (LinkedIn, Naukri,
Indeed India) with domain-aware rate limiting, deduplicated storage via
asyncpg + pgvector, and a Celery task for orchestration with exponential
backoff.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class JobPosting:
    """Normalised job posting from any source."""
    source: str                       # linkedin | naukri | indeed
    source_job_id: str                # ID on the source platform
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_at: str = ""               # ISO-8601 or relative string
    salary: str = ""
    employment_type: str = ""         # full-time, contract, internship
    work_mode: str = ""               # remote, hybrid, on-site
    skills: list[str] = field(default_factory=list)
    experience_required: str = ""
    hash_key: str = ""                # dedup hash, set by storage layer
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now(timezone.utc).isoformat()
        # Build a reproducible hash for deduplication
        unique_str = f"{self.source}|{self.source_job_id}|{self.title}|{self.company}"
        self.hash_key = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

_DOMAIN_LIMITS: dict[str, tuple[int, float]] = {
    "linkedin": (10, 60.0),   # 10 requests per 60 seconds
    "naukri":   (8, 60.0),
    "indeed":   (10, 60.0),
}


class RateLimiter:
    """Domain-aware sliding-window rate limiter.

    Usage::

        rl = RateLimiter()
        async with rl.acquire("linkedin"):
            await make_request()
    """

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}  # domain -> timestamps

    def _clean(self, domain: str, window: float) -> None:
        now = time.monotonic()
        self._buckets[domain] = [
            ts for ts in self._buckets.get(domain, [])
            if now - ts < window
        ]

    async def acquire(self, domain: str) -> None:
        """Block until a slot is available for *domain*."""
        max_reqs, window = _DOMAIN_LIMITS.get(domain, (10, 60.0))

        while True:
            self._clean(domain, window)
            if len(self._buckets.get(domain, [])) < max_reqs:
                self._buckets.setdefault(domain, []).append(time.monotonic())
                return
            # Wait for one window cycle
            await asyncio.sleep(window / max_reqs)

    @property
    def stats(self) -> dict[str, int]:
        return {d: len(ts) for d, ts in self._buckets.items()}


# ---------------------------------------------------------------------------
# Base scraper
# ---------------------------------------------------------------------------

class BaseJobScraper(ABC):
    """Abstract base for job-board scrapers.

    Subclasses must implement :meth:`search` and set :attr:`source_name`.
    """

    source_name: str = "base"

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        http_client: httpx.AsyncClient | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.rate_limiter = rate_limiter or RateLimiter()
        self._http = http_client
        self._own_client = http_client is None
        self._headers = headers or {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        }

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                headers=self._headers,
                timeout=httpx.Timeout(30.0, connect=15.0),
                follow_redirects=True,
            )
        return self._http

    async def close(self) -> None:
        if self._own_client and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @abstractmethod
    async def search(
        self,
        query: str,
        location: str = "",
        max_pages: int = 1,
    ) -> list[JobPosting]:
        """Search jobs and return normalised JobPosting list."""
        ...

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def _normalise_location(self, raw: str) -> str:
        """Clean up location strings (India-centric)."""
        if not raw:
            return ""
        raw = raw.strip()
        # Drop common prefixes
        raw = re.sub(r"^(?:location[s]?[:\-]?\s*)", "", raw, flags=re.IGNORECASE)
        return raw.strip()


# ---------------------------------------------------------------------------
# LinkedIn Scraper
# ---------------------------------------------------------------------------

class LinkedInScraper(BaseJobScraper):
    """Scrapes LinkedIn India job search results.

    Uses the LinkedIn public job search page (HTML scraping).
    """

    source_name = "linkedin"
    BASE_URL = "https://www.linkedin.com/jobs/search"

    async def search(
        self,
        query: str,
        location: str = "India",
        max_pages: int = 2,
    ) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        client = await self._client()

        params = {
            "keywords": query,
            "location": location,
            "f_TPR": "",          # any time
            "position": 1,
        }

        for page in range(max_pages):
            params["start"] = page * 25
            url = f"{self.BASE_URL}?{urlencode(params)}"

            await self.rate_limiter.acquire("linkedin")
            logger.info("LinkedIn page %d: %s", page + 1, url)

            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning("LinkedIn HTTP error on page %d: %s", page + 1, exc)
                continue

            soup = self._soup(resp.text)
            cards = soup.select("div.base-card")

            if not cards:
                # Fallback: broader selector
                cards = soup.select("li[data-entity-urn^='urn:li:job']")

            for card in cards:
                try:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                except Exception:
                    logger.debug("Skipping unparseable LinkedIn card", exc_info=True)

            # Small delay between pages
            await asyncio.sleep(1.0)

        logger.info("LinkedIn returned %d jobs for query=%s", len(jobs), query)
        return jobs

    def _parse_card(self, card: BeautifulSoup) -> JobPosting | None:
        """Extract a single JobPosting from a LinkedIn job card."""
        # Title
        title_el = card.select_one("h3.base-search-card__title")
        if not title_el:
            title_el = card.select_one("a.job-card-list__title")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        # Company
        company_el = card.select_one("h4.base-search-card__subtitle")
        if not company_el:
            company_el = card.select_one("span.job-card-container__primary-description")
        company = company_el.get_text(strip=True) if company_el else ""

        # Location
        loc_el = card.select_one("span.job-search-card__location")
        if not loc_el:
            loc_el = card.select_one("span.job-card-container__metadata-item")
        location = self._normalise_location(loc_el.get_text(strip=True)) if loc_el else ""

        # URL
        link_el = card.select_one("a.base-card__full-link")
        if not link_el:
            link_el = card.select_one("a.job-card-list__title")
        url = urljoin("https://www.linkedin.com", link_el.get("href", "")) if link_el else ""

        # Source job ID from URL
        match = re.search(r"/jobs/view/(\d+)", url)
        source_job_id = match.group(1) if match else hashlib.md5(url.encode()).hexdigest()[:12]

        return JobPosting(
            source=self.source_name,
            source_job_id=source_job_id,
            title=title,
            company=company,
            location=location,
            description="",  # detail page would require a second request
            url=url,
        )


# ---------------------------------------------------------------------------
# Naukri Scraper
# ---------------------------------------------------------------------------

class NaukriScraper(BaseJobScraper):
    """Scrapes Naukri.com job listings via their public search API.

    Naukri is a Next.js SPA — job data is not in the HTML.  We use the
    public ``/jobapi/v1/search`` endpoint which returns structured JSON
    with job titles, companies, locations, salary, etc.
    """

    source_name = "naukri"
    BASE_URL = "https://www.naukri.com"
    API_URL = "https://www.naukri.com/jobapi/v1/search"

    async def search(
        self,
        query: str,
        location: str = "",
        max_pages: int = 2,
    ) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        client = await self._client()

        for page in range(1, max_pages + 1):
            params = {
                "query": query,
                "location": location or "India",
                "pageNo": page,
                "pageSize": 20,
            }
            url = f"{self.API_URL}?{urlencode(params)}"

            await self.rate_limiter.acquire("naukri")
            logger.info("Naukri page %d: %s", page, url)

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
                logger.warning("Naukri HTTP error on page %d: %s", page, exc)
                continue

            try:
                data = resp.json()
            except Exception:
                logger.warning("Naukri returned non-JSON on page %d", page)
                continue

            for item in data.get("list", []):
                try:
                    job = self._parse_api_item(item)
                    if job:
                        jobs.append(job)
                except Exception:
                    logger.debug("Skipping unparseable Naukri item", exc_info=True)

            logger.info("Naukri page %d: parsed %d jobs", page, len(data.get("list", [])))
            await asyncio.sleep(1.0)

        logger.info("Naukri returned %d jobs for query=%s", len(jobs), query)
        return jobs

    @staticmethod
    def _parse_api_item(item: dict) -> JobPosting | None:
        """Convert a Naukri API job dict to a JobPosting."""
        title = item.get("post", "") or item.get("tupleDesc", "")
        if not title:
            return None

        # Clean HTML from title
        title = re.sub(r"<[^>]+>", "", title).strip()
        if not title:
            return None

        company = item.get("companyName", "") or item.get("CONTCOM", "")
        location = item.get("cityfield", "")
        # Clean up location string
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

        # Employment type
        employment_type = item.get("employmentType", "")

        # Description (strip HTML)
        job_desc = item.get("jobDesc", "") or ""
        description = re.sub(r"<[^>]+>", " ", job_desc).strip()[:2000] if job_desc else ""

        # URL
        url = item.get("urlStr", "") or item.get("nonStaticUrlFor", "")
        if url and not url.startswith("http"):
            url = urljoin("https://www.naukri.com", url)

        # Job ID for dedup
        source_job_id = str(item.get("jobId", "")) or hashlib.md5(url.encode()).hexdigest()[:12]

        # Keywords as skills proxy
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


# ---------------------------------------------------------------------------
# Indeed India Scraper (Stub with proper structure)
# ---------------------------------------------------------------------------

class IndeedIndiaScraper(BaseJobScraper):
    """Indeed India job scraper.

    Scrapes the Indeed India public job search page.  Indeed uses
    obfuscated CSS class names that change frequently, so we try a broad
    set of selectors and also fall back to JSON-LD structured data
    embedded in the page (``<script type="application/ld+json">``) which
    is more stable.

    For production at scale, consider Indeed's Publisher API or a proxy
    rotation service (ScrapingBee, BrightData).
    """

    source_name = "indeed"
    BASE_URL = "https://in.indeed.com"

    async def search(
        self,
        query: str,
        location: str = "",
        max_pages: int = 2,
    ) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        client = await self._client()

        for page in range(max_pages):
            params = {
                "q": query,
                "l": location or "India",
                "start": page * 10,
                "sort": "date",
            }
            url = f"{self.BASE_URL}/jobs?{urlencode(params)}"

            await self.rate_limiter.acquire("indeed")
            logger.info("Indeed page %d: %s", page + 1, url)

            try:
                resp = await client.get(
                    url,
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-IN,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Cache-Control": "max-age=0",
                    },
                    follow_redirects=True,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning("Indeed HTTP error on page %d: %s", page + 1, exc)
                # If 403, try the RSS feed fallback
                if exc.response is not None and exc.response.status_code == 403:
                    logger.info("Indeed blocked direct scraping, trying RSS feed fallback")
                    rss_jobs = await self._rss_fallback(client, query, location or "India")
                    jobs.extend(rss_jobs)
                continue

            soup = self._soup(resp.text)
            page_jobs: list[JobPosting] = []

            # Strategy 1: JSON-LD structured data (most reliable)
            json_ld_jobs = self._parse_json_ld(soup)
            if json_ld_jobs:
                page_jobs.extend(json_ld_jobs)

            # Strategy 2: HTML card scraping (fallback)
            if not page_jobs:
                html_jobs = self._parse_html_cards(soup)
                page_jobs.extend(html_jobs)

            jobs.extend(page_jobs)
            logger.info("Indeed page %d: parsed %d jobs", page + 1, len(page_jobs))

            await asyncio.sleep(2.0)  # Indeed is aggressive about rate detection

        logger.info("Indeed returned %d jobs for query=%s", len(jobs), query)
        return jobs

    async def _rss_fallback(
        self, client: httpx.AsyncClient, query: str, location: str
    ) -> list[JobPosting]:
        """Fallback: use Indeed's RSS feed when direct scraping is blocked."""
        import xml.etree.ElementTree as ET

        rss_url = f"{self.BASE_URL}/rss?q={urlencode({'q': query})}&l={urlencode({'l': location or 'India'})}"
        logger.info("Indeed RSS fallback: %s", rss_url)

        try:
            resp = await client.get(rss_url)
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            logger.warning("Indeed RSS fallback also failed")
            return []

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            logger.warning("Indeed RSS returned invalid XML")
            return []

        jobs: list[JobPosting] = []
        # RSS 2.0
        for item in root.findall(".//item")[:20]:
            title_el = item.find("title")
            link_el = item.find("link")
            if title_el is None:
                continue
            title = title_el.text or ""
            url = link_el.text or "" if link_el is not None else ""
            if not title:
                continue

            # Try to extract company from title (common pattern: "Job Title - Company")
            company = ""
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                company = parts[1].strip()

            jobs.append(JobPosting(
                source="indeed",
                source_job_id=hashlib.md5(url.encode()).hexdigest()[:12],
                title=title,
                company=company,
                description="",
                url=url,
            ))

        logger.info("Indeed RSS fallback returned %d jobs", len(jobs))
        return jobs

    # -- JSON-LD parsing (Strategy 1) -----------------------------------

    def _parse_json_ld(self, soup: BeautifulSoup) -> list[JobPosting]:
        """Extract jobs from ``<script type="application/ld+json">`` blocks.

        Indeed embeds ``JobPosting`` schema.org structured data in the
        search results page.  This is more stable than CSS selectors.
        """
        import json as _json

        jobs: list[JobPosting] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = _json.loads(script.string or "")
            except (_json.JSONDecodeError, TypeError):
                continue

            # The page may contain a single JobPosting or a list under @graph
            items = []
            if isinstance(data, dict) and data.get("@graph"):
                items = data["@graph"]
            elif isinstance(data, dict) and data.get("@type") == "JobPosting":
                items = [data]
            elif isinstance(data, dict) and data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
            elif isinstance(data, list):
                items = data

            for item in items:
                if isinstance(item, dict):
                    job = self._parse_json_ld_item(item)
                    if job:
                        jobs.append(job)

        return jobs

    @staticmethod
    def _parse_json_ld_item(item: dict) -> JobPosting | None:
        """Convert a single JSON-LD JobPosting dict to a JobPosting."""
        title = item.get("title", "")
        if not title:
            return None

        # hiringOrganization can be a string or a dict
        hiring_org = item.get("hiringOrganization", {})
        company = ""
        if isinstance(hiring_org, dict):
            company = hiring_org.get("name", "")
        elif isinstance(hiring_org, str):
            company = hiring_org

        # jobLocation can be a string or a dict with address
        job_loc = item.get("jobLocation", {})
        location = ""
        if isinstance(job_loc, dict):
            address = job_loc.get("address", {})
            if isinstance(address, dict):
                location = address.get("addressLocality", "") or address.get("addressRegion", "")
            elif address:
                location = str(address)
        elif isinstance(job_loc, str):
            location = job_loc

        # URL
        url = item.get("url", "")

        # description
        description = item.get("description", "")

        # datePosted
        posted_at = item.get("datePosted", "")

        # identifier
        source_job_id = str(item.get("identifier", {}).get("value", "")) if isinstance(item.get("identifier"), dict) else ""

        # salary from baseSalary
        salary = ""
        base_salary = item.get("baseSalary", {})
        if isinstance(base_salary, dict):
            value = base_salary.get("value", {})
            if isinstance(value, dict):
                min_val = value.get("minValue", "")
                max_val = value.get("maxValue", "")
                currency = value.get("currency", "INR")
                if min_val and max_val:
                    salary = f"{currency} {min_val} - {max_val}"
                elif min_val:
                    salary = f"{currency} {min_val}+"

        # employmentType
        employment_type = item.get("employmentType", "")

        # experienceRequired (not standard in schema.org but Indeed sometimes includes it)
        experience_required = item.get("experienceRequirements", "") or item.get("experienceRequired", "")

        # skills (not standard but sometimes present)
        skills_raw = item.get("skills", [])
        skills = [s.strip() for s in skills_raw] if isinstance(skills_raw, list) else []

        return JobPosting(
            source="indeed",
            source_job_id=source_job_id or hashlib.md5(url.encode()).hexdigest()[:12],
            title=title,
            company=company,
            location=location,
            description=description[:2000] if description else "",
            url=url,
            posted_at=posted_at,
            salary=salary,
            employment_type=employment_type if isinstance(employment_type, str) else "",
            skills=skills,
            experience_required=experience_required if isinstance(experience_required, str) else "",
        )

    # -- HTML card parsing (Strategy 2, fallback) ---------------------

    def _parse_html_cards(self, soup: BeautifulSoup) -> list[JobPosting]:
        """Fallback: parse jobs from HTML card elements."""
        jobs: list[JobPosting] = []

        cards = (
            soup.select("div.job_seen_beacon")
            or soup.select("div[data-testid='job-card']")
            or soup.select("div.jobCard")
            or soup.select("li[data-ocg-job]")
            or soup.select("div.jobsearch-SerpJobCard")
            or soup.select("td.resultContent")
        )

        for card in cards:
            try:
                job = self._parse_html_card(card)
                if job:
                    jobs.append(job)
            except Exception:
                logger.debug("Skipping unparseable Indeed card", exc_info=True)

        return jobs

    def _parse_html_card(self, card: BeautifulSoup) -> JobPosting | None:
        title_el = (
            card.select_one("h2.jobTitle a")
            or card.select_one("a[data-testid='job-card-title']")
            or card.select_one("a[class*='title']")
            or card.select_one("a.jobtitle")
        )
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        company_el = (
            card.select_one("span[data-testid='company-name']")
            or card.select_one("span.companyName")
            or card.select_one("span[class*='company']")
        )
        company = company_el.get_text(strip=True) if company_el else ""

        loc_el = (
            card.select_one("div[data-testid='job-card-location']")
            or card.select_one("span[class*='location']")
        )
        location = self._normalise_location(loc_el.get_text(strip=True)) if loc_el else ""

        link = title_el.get("href", "") if title_el else ""
        url = urljoin(self.BASE_URL, link) if link else ""

        job_id = ""
        if url:
            match = re.search(r"/viewjob\?jk=([\w]+)", url)
            if match:
                job_id = match.group(1)
            else:
                job_id = hashlib.md5(url.encode()).hexdigest()[:12]

        return JobPosting(
            source=self.source_name,
            source_job_id=job_id,
            title=title,
            company=company,
            location=location,
            description="",
            url=url,
        )


# ---------------------------------------------------------------------------
# Job Storage (asyncpg + pgvector)
# ---------------------------------------------------------------------------

class JobStorage:
    """Persist jobs to PostgreSQL with deduplication.

    Deduplication happens at two levels:
      1. **Hash key** — exact match on ``source|source_job_id|title|company``.
      2. **Semantic** (optional) — pgvector cosine similarity check for
         near-duplicate descriptions (threshold: 0.92).
    """

    DDL = """
    CREATE TABLE IF NOT EXISTS careerpilot_jobs (
        id              BIGSERIAL PRIMARY KEY,
        hash_key        TEXT UNIQUE NOT NULL,
        source          TEXT NOT NULL,
        source_job_id   TEXT NOT NULL,
        title           TEXT NOT NULL,
        company         TEXT NOT NULL DEFAULT '',
        location        TEXT NOT NULL DEFAULT '',
        description     TEXT NOT NULL DEFAULT '',
        url             TEXT NOT NULL DEFAULT '',
        posted_at       TEXT NOT NULL DEFAULT '',
        salary          TEXT NOT NULL DEFAULT '',
        employment_type TEXT NOT NULL DEFAULT '',
        work_mode       TEXT NOT NULL DEFAULT '',
        skills          TEXT[] DEFAULT '{}',
        experience_required TEXT NOT NULL DEFAULT '',
        embedding       vector(384),          -- all-MiniLM-L6-v2 dimension
        scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_careerpilot_jobs_hash ON careerpilot_jobs(hash_key);
    CREATE INDEX IF NOT EXISTS idx_careerpilot_jobs_source ON careerpilot_jobs(source);
    CREATE INDEX IF NOT EXISTS idx_careerpilot_jobs_embedding
        ON careerpilot_jobs USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or ""
        self._pool: Any = None

    async def connect(self) -> None:
        """Create connection pool."""
        import asyncpg
        import os

        if not self.dsn:
            self.dsn = os.environ.get("DATABASE_URL", "")
        if not self.dsn:
            raise ValueError(
                "Database DSN required. Pass dsn or set DATABASE_URL env var."
            )
        # asyncpg doesn't understand the +asyncpg suffix in SQLAlchemy DSNs
        dsn = self.dsn.replace("+asyncpg", "")
        self._pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        await self._init_schema()

    async def _init_schema(self) -> None:
        async with self._pool.acquire() as conn:
            # Enable pgvector if not already
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(self.DDL)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def job_exists(self, hash_key: str) -> bool:
        """Check if a job with this hash already exists."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM careerpilot_jobs WHERE hash_key = $1", hash_key
            )
            return row is not None

    async def store_job(self, job: JobPosting, embedding: list[float] | None = None) -> bool:
        """Insert a job posting if it doesn't exist. Returns True if inserted."""
        if await self.job_exists(job.hash_key):
            return False

        async with self._pool.acquire() as conn:
            # Convert scraped_at string to datetime if needed
            scraped_at = job.scraped_at
            if isinstance(scraped_at, str):
                from datetime import datetime, timezone
                try:
                    # Handle ISO format strings with or without timezone
                    if scraped_at.endswith('Z'):
                        scraped_at = datetime.fromisoformat(scraped_at[:-1] + '+00:00')
                    else:
                        scraped_at = datetime.fromisoformat(scraped_at)
                    # Ensure timezone-aware (asyncpg prefers timezone-aware for timestamptz)
                    if scraped_at.tzinfo is None:
                        scraped_at = scraped_at.replace(tzinfo=timezone.utc)
                except ValueError:
                    # If parsing fails, use current time
                    scraped_at = datetime.now(timezone.utc)
            
            await conn.execute(
                """
                INSERT INTO careerpilot_jobs
                    (hash_key, source, source_job_id, title, company, location,
                     description, url, posted_at, salary, employment_type,
                     work_mode, skills, experience_required, embedding, scraped_at)
                VALUES
                    ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (hash_key) DO NOTHING
                """,
                job.hash_key,
                job.source,
                job.source_job_id,
                job.title,
                job.company,
                job.location,
                job.description,
                job.url,
                job.posted_at,
                job.salary,
                job.employment_type,
                job.work_mode,
                job.skills,
                job.experience_required,
                embedding,
                scraped_at,
            )
        return True

    async def get_similar_jobs(
        self,
        embedding: list[float],
        threshold: float = 0.92,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find jobs whose embedding is close to *embedding* (semantic dedup)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT hash_key, title, company, description,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM careerpilot_jobs
                WHERE embedding IS NOT NULL
                  AND 1 - (embedding <=> $1::vector) >= $2
                ORDER BY similarity DESC
                LIMIT $3
                """,
                embedding,
                threshold,
                limit,
            )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Job filter
# ---------------------------------------------------------------------------

_MINIMUM_JOB_TITLE_LENGTH = 5
_EXCLUDED_KEYWORDS = [
    "internship", "trainee", "volunteer", "unpaid",
    "walk-in", "walkin",
]


def should_include_job(job: JobPosting, min_salary: str = "") -> bool:
    """Heuristic filter for job relevance.

    Returns False if the job's title or description contains exclusion
    keywords or fails basic quality checks.
    """
    title = (job.title or "").lower().strip()
    desc = (job.description or "").lower()
    combined = f"{title} {desc}"

    if len(title) < _MINIMUM_JOB_TITLE_LENGTH:
        return False

    for kw in _EXCLUDED_KEYWORDS:
        if kw in combined:
            return False

    # Basic salary filter if a minimum was provided
    if min_salary and job.salary:
        try:
            nums = re.findall(r"(\d[\d,]*\.?\d*)", job.salary)
            if nums:
                # Take the smallest number in the salary string
                salary_val = min(float(n.replace(",", "")) for n in nums)
                # Convert min_salary similarly
                min_val = float(re.sub(r"[^0-9.]", "", min_salary))
                if salary_val < min_val:
                    return False
        except (ValueError, TypeError):
            pass

    return True


# ---------------------------------------------------------------------------
# Celery orchestrator
# ---------------------------------------------------------------------------

try:
    from celery import Celery as _Celery

    _celery_app = _Celery("careerpilot")
except ImportError:
    _celery_app = None
    logger.warning("Celery not installed. run_all_sources will run synchronously.")


def _get_celery() -> Any:
    """Return the Celery app or None."""
    return _celery_app


async def _scrape_source(
    scraper: BaseJobScraper,
    query: str,
    location: str,
    storage: JobStorage,
    max_pages: int = 2,
) -> int:
    """Run a single scraper and store results. Returns count of new jobs."""
    new_jobs = 0
    try:
        postings = await scraper.search(query, location, max_pages)
        for job in postings:
            if should_include_job(job):
                stored = await storage.store_job(job)
                if stored:
                    new_jobs += 1
                    logger.debug("Stored: %s @ %s", job.title, job.company)
    except Exception:
        logger.exception("Scraper %s failed", scraper.source_name)
    finally:
        await scraper.close()
    return new_jobs


async def run_all_sources_async(
    query: str,
    location: str = "India",
    max_pages: int = 2,
    dsn: str | None = None,
) -> dict[str, int]:
    """Scrape all sources and persist results. Returns per-source counts."""
    storage = JobStorage(dsn)
    await storage.connect()

    rate_limiter = RateLimiter()

    scrapers: list[BaseJobScraper] = [
        LinkedInScraper(rate_limiter=rate_limiter),
        NaukriScraper(rate_limiter=rate_limiter),
        IndeedIndiaScraper(rate_limiter=rate_limiter),
    ]

    results: dict[str, int] = {}
    try:
        for scraper in scrapers:
            count = await _scrape_source(scraper, query, location, storage, max_pages)
            results[scraper.source_name] = count
            logger.info("%s: %d new jobs", scraper.source_name, count)
    finally:
        await storage.close()

    return results


def run_all_sources(
    query: str,
    location: str = "India",
    max_pages: int = 2,
    dsn: str | None = None,
    max_retries: int = 3,
) -> dict[str, int]:
    """Synchronous entry point (Celery task, or direct call).

    Implements exponential backoff on failure.
    """
    import asyncio

    last_exc: Exception | None = None
    delay = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            return asyncio.run(
                run_all_sources_async(query, location, max_pages, dsn)
            )
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "run_all_sources attempt %d/%d failed: %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                import random
                sleep_secs = delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.info("Backing off %.1f s ...", sleep_secs)
                time.sleep(sleep_secs)

    raise RuntimeError(
        f"run_all_sources failed after {max_retries} attempts"
    ) from last_exc


# Celery task wrapper (registered if Celery is available)
if _celery_app is not None:

    @_celery_app.task(
        bind=True,
        max_retries=3,
        default_retry_delay=30,
        autoretry_for=(Exception,),
    )
    def run_all_sources_task(
        self,
        query: str,
        location: str = "India",
        max_pages: int = 2,
        dsn: str | None = None,
    ) -> dict[str, int]:
        """Celery task wrapping run_all_sources."""
        return run_all_sources(query, location, max_pages, dsn)
