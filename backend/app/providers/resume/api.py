"""
CareerPilot AI — API-based Resume Analysis Provider
=====================================================
Uses an external HTTP API to parse resumes.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx

from app.providers.base import ResumeProvider, UserProfile

logger = logging.getLogger(__name__)


class ApiResumeProvider(ResumeProvider):
    """Sends resume text to an external parsing API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_url = (api_url or os.getenv("RESUME_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("RESUME_API_KEY", "")
        self.timeout = timeout

        if not self.api_url:
            raise ValueError(
                "RESUME_API_URL is required for ApiResumeProvider. "
                "Set it via env var or the constructor."
            )

    def parse(self, resume_text: str) -> UserProfile:
        """Parse resume text via the external API."""
        import httpx

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(
            "API Resume -> POST %s/parse (%d chars)",
            self.api_url,
            len(resume_text),
        )

        resp = httpx.post(
            f"{self.api_url}/parse",
            json={"resume_text": resume_text},
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        return self._convert_response(data)

    def parse_with_embedding(self, resume_text: str) -> UserProfile:
        """Parse resume and request embedding from the API in one call."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = httpx.post(
            f"{self.api_url}/parse-with-embedding",
            json={"resume_text": resume_text},
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        return self._convert_response(data)

    # ------------------------------------------------------------------
    #  Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_response(data: dict) -> UserProfile:
        """Convert API response dict to UserProfile."""
        profile_data = data.get("profile", data.get("data", data))
        return UserProfile(
            full_name=profile_data.get("full_name", ""),
            email=profile_data.get("email", ""),
            phone=profile_data.get("phone", ""),
            linkedin_url=profile_data.get("linkedin_url", ""),
            github_url=profile_data.get("github_url", ""),
            portfolio_url=profile_data.get("portfolio_url", ""),
            summary=profile_data.get("summary", ""),
            skills=profile_data.get("skills", []),
            soft_skills=profile_data.get("soft_skills", []),
            work_experience=profile_data.get("work_experience", []),
            education=profile_data.get("education", []),
            certifications=profile_data.get("certifications", []),
            languages=profile_data.get("languages", []),
            total_years_experience=profile_data.get("total_years_experience", 0.0),
            current_role=profile_data.get("current_role", ""),
            preferred_roles=profile_data.get("preferred_roles", []),
            preferred_locations=profile_data.get("preferred_locations", []),
            employment_type=profile_data.get("employment_type", ""),
            salary_expectation=profile_data.get("salary_expectation", ""),
            embedding=profile_data.get("embedding", None),
        )

    @staticmethod
    def extract_text(file_path: str | Path) -> str:
        """Extract text locally before sending to the API."""
        from app.providers.resume.native import NativeResumeProvider

        return NativeResumeProvider.extract_text(file_path)
