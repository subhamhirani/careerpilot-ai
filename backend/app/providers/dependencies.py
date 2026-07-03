"""
CareerPilot AI — Provider Dependency Injection
================================================
FastAPI dependencies for injecting providers into routers.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends

from app.providers.base import (
    MatcherProvider,
    ResumeProvider,
    ScraperProvider,
)
from app.providers.factory import ProviderFactory


def get_scraper_provider(name: str = "native", **kwargs: Any) -> ScraperProvider:
    """Dependency factory: returns a scraper provider by name.

    Usage in a router::

        from fastapi import Depends
        from app.providers.base import ScraperProvider
        from app.providers.dependencies import get_scraper_provider

        @router.post("/scrape")
        async def scrape(
            provider: ScraperProvider = Depends(get_scraper_provider),
        ):
            result = await provider.scrape(...)
    """
    return ProviderFactory.create_scraper(name, **kwargs)


def get_resume_provider(name: str = "native", **kwargs: Any) -> ResumeProvider:
    """Dependency factory: returns a resume analysis provider by name."""
    return ProviderFactory.create_resume(name, **kwargs)


def get_matcher_provider(name: str = "native", **kwargs: Any) -> MatcherProvider:
    """Dependency factory: returns a matcher provider by name."""
    return ProviderFactory.create_matcher(name, **kwargs)
