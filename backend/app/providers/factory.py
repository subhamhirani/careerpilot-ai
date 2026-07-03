"""
CareerPilot AI — Provider Factory & Registry
==============================================
"""
from __future__ import annotations

import logging
from typing import Any

from app.providers.base import (
    MatcherProvider,
    ResumeProvider,
    ScraperProvider,
)

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Registry + factory for all providers."""

    _scraper_providers: dict[str, type[ScraperProvider]] = {}
    _resume_providers: dict[str, type[ResumeProvider]] = {}
    _matcher_providers: dict[str, type[MatcherProvider]] = {}

    # ------------------------------------------------------------------
    #  Registration
    # ------------------------------------------------------------------

    @classmethod
    def register_scraper(cls, name: str, provider_cls: type[ScraperProvider]) -> None:
        cls._scraper_providers[name] = provider_cls
        logger.debug("Registered scraper provider: %s", name)

    @classmethod
    def register_resume(cls, name: str, provider_cls: type[ResumeProvider]) -> None:
        cls._resume_providers[name] = provider_cls
        logger.debug("Registered resume provider: %s", name)

    @classmethod
    def register_matcher(cls, name: str, provider_cls: type[MatcherProvider]) -> None:
        cls._matcher_providers[name] = provider_cls
        logger.debug("Registered matcher provider: %s", name)

    # ------------------------------------------------------------------
    #  Creation
    # ------------------------------------------------------------------

    @classmethod
    def create_scraper(
        cls,
        name: str = "native",
        **kwargs: Any,
    ) -> ScraperProvider:
        if name not in cls._scraper_providers:
            raise ValueError(
                f"Unknown scraper provider: {name!r}. "
                f"Available: {list(cls._scraper_providers)}"
            )
        return cls._scraper_providers[name](**kwargs)

    @classmethod
    def create_resume(
        cls,
        name: str = "native",
        **kwargs: Any,
    ) -> ResumeProvider:
        if name not in cls._resume_providers:
            raise ValueError(
                f"Unknown resume provider: {name!r}. "
                f"Available: {list(cls._resume_providers)}"
            )
        return cls._resume_providers[name](**kwargs)

    @classmethod
    def create_matcher(
        cls,
        name: str = "native",
        **kwargs: Any,
    ) -> MatcherProvider:
        if name not in cls._matcher_providers:
            raise ValueError(
                f"Unknown matcher provider: {name!r}. "
                f"Available: {list(cls._matcher_providers)}"
            )
        return cls._matcher_providers[name](**kwargs)

    # ------------------------------------------------------------------
    #  Listing
    # ------------------------------------------------------------------

    @classmethod
    def available_scrapers(cls) -> list[str]:
        return list(cls._scraper_providers)

    @classmethod
    def available_resume(cls) -> list[str]:
        return list(cls._resume_providers)

    @classmethod
    def available_matchers(cls) -> list[str]:
        return list(cls._matcher_providers)
