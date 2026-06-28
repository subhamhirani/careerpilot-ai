"""
CareerPilot AI — Agent 1: Resume Analysis Agent
================================================
Extracts text from PDF/DOCX resumes, parses structured data via Groq
(llama-3.3-70b-versatile), and generates embedding vectors with
sentence-transformers for semantic matching.
"""

from __future__ import annotations

import io
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Module-level model cache to avoid re-instantiation overhead
_MODEL_CACHE: dict[str, Any] = {}

# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def extract_text_from_pdf(path: str | Path) -> str:
    """Extract plain text from a PDF file using pdfplumber."""
    import pdfplumber

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    logger.info("Extracting text from PDF: %s", path)
    fragments: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                fragments.append(text)
    result = "\n\n".join(fragments).strip()
    logger.info("Extracted %d characters from PDF", len(result))
    return result


def extract_text_from_docx(path: str | Path) -> str:
    """Extract plain text from a .docx file using python-docx."""
    from docx import Document

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {path}")

    logger.info("Extracting text from DOCX: %s", path)
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    result = "\n\n".join(paragraphs).strip()
    logger.info("Extracted %d characters from DOCX", len(result))
    return result


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

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
    employment_type: str = ""  # full-time, contract, hybrid, remote
    salary_expectation: str = ""
    embedding: list[float] | None = None  # populated after generation

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("embedding", None)
        return d

    def profile_text(self) -> str:
        """Concatenate key fields into a single searchable text blob."""
        parts = [
            self.summary,
            " ".join(self.skills),
            " ".join(self.soft_skills),
            self.current_role,
            " ".join(self.preferred_roles),
            " ".join(self.preferred_locations),
            self.employment_type,
        ]
        for exp in self.work_experience:
            parts.append(exp.get("title", ""))
            parts.append(exp.get("company", ""))
            parts.append(exp.get("description", ""))
        for edu in self.education:
            parts.append(edu.get("degree", ""))
            parts.append(edu.get("field", ""))
            parts.append(edu.get("institution", ""))
        return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Resume Parser (Groq-powered)
# ---------------------------------------------------------------------------

_RESUME_SYSTEM_PROMPT = """\
You are a precise resume parser. Extract structured information from the resume text below and return a **valid JSON object only** — no preamble, no markdown fences.

The JSON must match this schema:
{
  "full_name": "",
  "email": "",
  "phone": "",
  "linkedin_url": "",
  "github_url": "",
  "portfolio_url": "",
  "summary": "",
  "skills": [],
  "soft_skills": [],
  "work_experience": [
    {
      "title": "",
      "company": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "current": false,
      "description": "",
      "technologies": []
    }
  ],
  "education": [
    {
      "degree": "",
      "field": "",
      "institution": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "gpa": ""
    }
  ],
  "certifications": [],
  "languages": [],
  "total_years_experience": 0.0,
  "current_role": "",
  "preferred_roles": [],
  "preferred_locations": [],
  "employment_type": "",
  "salary_expectation": ""
}

Rules:
- Extract ONLY what is explicitly present in the resume. Do not invent.
- `email` and `phone` should be normalised.
- `total_years_experience` should be a float (inferred from work dates if possible).
- `current_role` is the most recent job title.
- `preferred_roles`: if a "Desired Role" or "Objective" section exists, extract it.
- `skills` are technical/hard skills. `soft_skills` are interpersonal skills.
- `work_experience` list order: most recent first.
- If a field is missing use empty string / empty list / 0.0.
- Return ONLY valid JSON."""


class ResumeParser:
    """Parse resume text into a structured UserProfile using Groq LLM."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: Any = None

    def _get_client(self):
        """Lazy-init Groq client so import doesn't require it."""
        if self._client is not None:
            return self._client
        try:
            from groq import Groq as _Groq
        except ImportError:
            raise ImportError(
                "The 'groq' package is required. Install with: pip install groq"
            )
        if not self.api_key:
            import os

            self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Pass api_key or set GROQ_API_KEY env var."
            )
        self._client = _Groq(api_key=self.api_key)
        return self._client

    def parse(self, resume_text: str) -> UserProfile:
        """Parse raw resume text and return a UserProfile dataclass."""
        if not resume_text.strip():
            raise ValueError("Empty resume text provided.")

        client = self._get_client()

        logger.info(
            "Parsing resume (%d chars) with model=%s", len(resume_text), self.model
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _RESUME_SYSTEM_PROMPT},
                {"role": "user", "content": f"Resume text:\n\n{resume_text}"},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        if not raw:
            raise RuntimeError("Groq returned empty response for resume parsing.")

        # Defensive parse: strip any stray markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("JSON parse error from Groq output: %s", exc)
            logger.debug("Raw output:\n%s", raw)
            raise ValueError(f"Failed to parse Groq response as JSON: {exc}") from exc

        profile = UserProfile(**{
            k: data.get(k, v)
            for k, v in asdict(UserProfile()).items()
        })
        logger.info(
            "Successfully parsed resume for: %s", profile.full_name or "<unknown>"
        )
        return profile

    def parse_with_embedding(
        self,
        resume_text: str,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> UserProfile:
        """Parse resume and generate an embedding vector in one call."""
        profile = self.parse(resume_text)
        profile.embedding = self._generate_embedding(profile.profile_text(), model_name)
        return profile

    @staticmethod
    def _generate_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
        """Generate a sentence-transformer embedding for a text blob."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers required. Install: pip install sentence-transformers"
            )
        logger.info("Generating embedding with model=%s (%d chars)", model_name, len(text))
        if model_name not in _MODEL_CACHE:
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
        model = _MODEL_CACHE[model_name]
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
