"""
CareerPilot AI — Native Resume Analysis Provider
==================================================
Wraps the existing Groq-based ResumeParser behind the provider interface.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from app.providers.base import ResumeProvider, UserProfile

logger = logging.getLogger(__name__)


class NativeResumeProvider(ResumeProvider):
    """Uses the existing Groq-based resume parser and sentence-transformers."""

    def __init__(
        self,
        groq_api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        self.api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model

    def parse(self, resume_text: str) -> UserProfile:
        """Parse raw resume text using Groq LLM."""
        from app.agents.resume_analysis import ResumeParser as LegacyParser

        parser = LegacyParser(api_key=self.api_key or None, model=self.model)
        legacy_profile = parser.parse(resume_text)

        return self._convert_profile(legacy_profile)

    def parse_with_embedding(self, resume_text: str) -> UserProfile:
        """Parse resume and generate embedding in one call."""
        from app.agents.resume_analysis import ResumeParser as LegacyParser

        parser = LegacyParser(api_key=self.api_key or None, model=self.model)
        legacy_profile = parser.parse_with_embedding(resume_text)

        return self._convert_profile(legacy_profile)

    # ------------------------------------------------------------------
    #  Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_profile(legacy: Any) -> UserProfile:
        """Convert a legacy UserProfile dataclass to the provider-interface one."""
        return UserProfile(
            full_name=getattr(legacy, "full_name", ""),
            email=getattr(legacy, "email", ""),
            phone=getattr(legacy, "phone", ""),
            linkedin_url=getattr(legacy, "linkedin_url", ""),
            github_url=getattr(legacy, "github_url", ""),
            portfolio_url=getattr(legacy, "portfolio_url", ""),
            summary=getattr(legacy, "summary", ""),
            skills=getattr(legacy, "skills", []),
            soft_skills=getattr(legacy, "soft_skills", []),
            work_experience=getattr(legacy, "work_experience", []),
            education=getattr(legacy, "education", []),
            certifications=getattr(legacy, "certifications", []),
            languages=getattr(legacy, "languages", []),
            total_years_experience=getattr(legacy, "total_years_experience", 0.0),
            current_role=getattr(legacy, "current_role", ""),
            preferred_roles=getattr(legacy, "preferred_roles", []),
            preferred_locations=getattr(legacy, "preferred_locations", []),
            employment_type=getattr(legacy, "employment_type", ""),
            salary_expectation=getattr(legacy, "salary_expectation", ""),
            embedding=getattr(legacy, "embedding", None),
        )

    @staticmethod
    def extract_text(file_path: str | Path) -> str:
        """Extract plain text from a PDF or DOCX file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        if ext == ".pdf":
            from app.agents.resume_analysis import extract_text_from_pdf
            return extract_text_from_pdf(str(path))
        elif ext == ".docx":
            from app.agents.resume_analysis import extract_text_from_docx
            return extract_text_from_docx(str(path))
        else:
            # Treat as raw text file
            return path.read_text(encoding="utf-8", errors="replace")
