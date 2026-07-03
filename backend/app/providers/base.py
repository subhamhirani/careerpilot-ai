"""
CareerPilot AI — Provider Abstract Base Classes
=================================================
Defines the interface that every provider (native or API) must implement.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Shared data models
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    """Result from a resume-to-job matching operation."""
    overall_score: float
    grade: str = ""
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    keyword_score: float = 0.0
    skill_score: float = 0.0
    location_match: float = 0.0
    raw_data: dict[str, Any] = field(default_factory=dict)
    provider: str = ""

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UserProfile:
    """Structured profile extracted from a resume."""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    work_experience: list[dict[str, Any]] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    total_years_experience: float = 0.0
    current_role: str = ""
    preferred_roles: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    employment_type: str = ""
    salary_expectation: str = ""
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("embedding", None)
        return d


# ---------------------------------------------------------------------------
# Scraper Provider Interface
# ---------------------------------------------------------------------------

class ScraperProvider(ABC):
    """Abstract job scraper.

    Every scraper provider (native or API) must implement ``search()``
    and expose a ``source_name`` attribute.
    """

    source_name: str = "unknown"

    @abstractmethod
    async def search(
        self,
        queries: list[str] | None = None,
        location: str = "India",
        max_pages_per_query: int = 1,
        **kwargs: Any,
    ) -> list[JobPosting]:
        """Search for jobs and return a list of JobPosting objects."""
        ...


# ---------------------------------------------------------------------------
# Resume Analysis Provider Interface
# ---------------------------------------------------------------------------

class ResumeProvider(ABC):
    """Abstract resume parser / analyser.

    Every resume provider (native or API) must implement ``parse()``
    and optionally ``parse_with_embedding()``.
    """

    @abstractmethod
    def parse(self, resume_text: str) -> UserProfile:
        """Parse raw resume text into a structured UserProfile."""
        ...

    def parse_with_embedding(self, resume_text: str) -> UserProfile:
        """Parse resume and generate an embedding vector in one call."""
        profile = self.parse(resume_text)
        return profile


# ---------------------------------------------------------------------------
# Job Matcher Provider Interface
# ---------------------------------------------------------------------------

class MatcherProvider(ABC):
    """Abstract job matching / relevance scorer."""

    @abstractmethod
    def score_job(
        self,
        profile: UserProfile | dict[str, Any],
        job: dict[str, Any],
    ) -> dict[str, Any]:
        """Score a single job against a user profile.

        Returns a dict with keys like:
          - total_score / overall_score (float)
          - grade (str): A+, A, B, C, D
          - matched_skills (list[str])
          - missing_skills (list[str])
          - reasons (dict)
        """
        ...

    @abstractmethod
    def match_resume(
        self,
        resume_text: str,
        jobs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Match a resume against a list of jobs. Returns scored matches."""
        ...
