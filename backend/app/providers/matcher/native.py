"""Native matcher provider — wraps the resume-matcher micro-service proxy."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.providers.base import MatcherProvider, MatchResult

logger = logging.getLogger(__name__)


class NativeMatcherProvider(MatcherProvider):
    """Proxies to the internal resume‑matcher micro‑service."""

    def __init__(
        self,
        service_url: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.service_url = (
            service_url or os.getenv("RESUME_MATCHER_URL", "http://careerpilot-resume-agent:8002")
        ).rstrip("/")
        self.timeout = timeout

    async def match(
        self,
        resume_text: str,
        job_description: str | None = None,
        **kwargs: Any,
    ) -> MatchResult:
        """Send resume to the micro‑service for matching."""
        user_id = kwargs.get("user_id", "anonymous")

        payload: dict[str, Any] = {
            "resume_text": resume_text,
        }
        if job_description:
            payload["job_description"] = job_description

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_id}",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            logger.info("Matcher -> POST %s/match", self.service_url)
            resp = await client.post(
                f"{self.service_url}/match",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return self._convert_result(data)

    @staticmethod
    def _convert_result(data: dict) -> MatchResult:
        return MatchResult(
            score=data.get("score", 0.0),
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            recommendations=data.get("recommendations", []),
            details=data,
        )
