"""API-based matcher provider — uses an external matching service."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.providers.base import MatcherProvider, MatchResult

logger = logging.getLogger(__name__)


class ApiMatcherProvider(MatcherProvider):
    """Sends matching requests to an external API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_url = (api_url or os.getenv("MATCHER_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("MATCHER_API_KEY", "")
        self.timeout = timeout

        if not self.api_url:
            raise ValueError(
                "MATCHER_API_URL is required for ApiMatcherProvider."
            )

    async def match(
        self,
        resume_text: str,
        job_description: str | None = None,
        **kwargs: Any,
    ) -> MatchResult:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {"resume_text": resume_text}
        if job_description:
            payload["job_description"] = job_description
        payload.update(kwargs)

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            logger.info("API Matcher -> POST %s/match", self.api_url)
            resp = await client.post(
                f"{self.api_url}/match",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return MatchResult(
            overall_score=data.get("score", 0.0),
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            raw_data=data,
        )
