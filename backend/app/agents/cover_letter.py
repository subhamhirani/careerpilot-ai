"""
CareerPilot AI — Agent 5: Cover Letter Generator
=================================================
Generates personalised, truthful cover letters for job applications.

Features:
  - Three tone options: formal, direct, friendly
  - Template structure: opening → exp para → achievement para → culture para → closing
  - 350 word max constraint
  - Company name and role auto-referenced from job posting
  - Output stored to cover_letters table linked to JobPosting
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from groq import Groq

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cover Letter Generator
# ---------------------------------------------------------------------------

class CoverLetterGenerator:
    """Agent 5: Generate a tailored cover letter for a job application.

    Usage::

        gen = CoverLetterGenerator()
        letter = gen.generate(
            resume_json=my_resume,
            job_title="DevOps Engineer",
            company_name="Acme Corp",
            job_description="...",
            tone="formal",
        )

    The returned letter is plain text, ≤350 words, with no fabricated
    content.
    """

    MODEL = "llama-3.3-70b-versatile"

    TONE_GUIDES: Dict[str, str] = {
        "formal": (
            "Write in a professional, business-appropriate tone. "
            "Use complete sentences and formal language."
        ),
        "direct": (
            "Write in a concise, confident tone. "
            "Get straight to the point with minimal fluff."
        ),
        "friendly": (
            "Write in a warm, approachable tone while remaining "
            "professional. Show personality."
        ),
    }

    LETTER_STRUCTURE = (
        "- Opening: Why this specific role at this company "
        "(1 sentence, specific to job description)\n"
        "- Para 1: Most relevant experience mapped to their top "
        "requirement\n"
        "- Para 2: One concrete achievement (use numbers only if "
        "they exist in the resume)\n"
        "- Para 3: Technology/culture fit\n"
        "- Closing: Call to action"
    )

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        if not self.client.api_key:
            raise ValueError(
                "GROQ_API_KEY must be set via environment variable or "
                "passed as api_key argument."
            )

    # -- Generation ---------------------------------------------------------

    def generate(
        self,
        resume_json: Dict[str, Any],
        job_title: str,
        company_name: str,
        job_description: str,
        tone: str = "formal",
    ) -> str:
        """Generate a cover letter and return it as plain text.

        Args:
            resume_json: Parsed resume data (from ResumeParser or dict).
            job_title: Target role title.
            company_name: Target company name.
            job_description: Full job description text.
            tone: One of ``"formal"``, ``"direct"``, ``"friendly"``.

        Returns:
            Cover letter text (≤350 words, plain text, no markdown).

        Raises:
            ValueError: If *tone* is not recognised.
        """
        tone_guide = self.TONE_GUIDES.get(tone)
        if tone_guide is None:
            raise ValueError(
                f"Unknown tone '{tone}'. Choose from: "
                f"{', '.join(self.TONE_GUIDES)}"
            )

        system_prompt = (
            "You are an expert cover letter writer. Write compelling, "
            "truthful cover letters.  Use ONLY facts from the provided "
            "resume.  Never fabricate any skill, achievement, or "
            "experience.  Return plain text only — no markdown."
        )

        user_prompt = (
            f"Write a professional cover letter using ONLY the facts "
            f"from this resume JSON.\n"
            f"Target: {company_name}, Role: {job_title}\n\n"
            f"{tone_guide}\n\n"
            f"Structure:\n{self.LETTER_STRUCTURE}\n\n"
            f"Max 350 words.  No fluff.  No fabrication.\n\n"
            f"Resume:\n{json.dumps(resume_json, indent=2)}\n\n"
            f"Job Description:\n{job_description}"
        )

        logger.info(
            "Generating cover letter for %s @ %s (tone=%s)",
            job_title, company_name, tone,
        )
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=self.MODEL,
            temperature=0.4,
            max_tokens=1000,
        )

        letter = response.choices[0].message.content.strip()
        logger.info(
            "Cover letter generated (%d chars)", len(letter)
        )
        return letter

    # -- Convenience: generate + prepare DB row ----------------------------

    @staticmethod
    def build_cover_letter_data(
        cover_letter_text: str,
        job_posting_id: str,
        user_id: str,
        tone: str = "formal",
    ) -> Dict[str, Any]:
        """Build a dict suitable for inserting into the ``cover_letters``
        table.

        Example::

            data = gen.build_cover_letter_data(
                letter_text, job_id, user_id, tone="direct"
            )
            await db.execute(cover_letters.insert().values(**data))
        """
        return {
            "job_posting_id": job_posting_id,
            "user_id": user_id,
            "content": cover_letter_text,
            "tone": tone,
            "word_count": len(cover_letter_text.split()),
            "created_at": None,  # let DB server_default handle it
        }


# ---------------------------------------------------------------------------
# Convenience entrypoint
# ---------------------------------------------------------------------------

async def run_cover_letter_generation(
    resume_json: Dict[str, Any],
    job_title: str,
    company_name: str,
    job_description: str,
    job_posting_id: str,
    user_id: str,
    tone: str = "formal",
) -> Dict[str, Any]:
    """High-level helper: generate cover letter + build DB payload.

    Designed for use from a Celery task or FastAPI endpoint.

    Returns::

        {
            "cover_letter": "...",
            "word_count": 285,
            "db_data": { ... },
        }
    """
    gen = CoverLetterGenerator()
    letter = gen.generate(
        resume_json=resume_json,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description,
        tone=tone,
    )
    db_data = gen.build_cover_letter_data(
        cover_letter_text=letter,
        job_posting_id=job_posting_id,
        user_id=user_id,
        tone=tone,
    )
    return {
        "cover_letter": letter,
        "word_count": len(letter.split()),
        "db_data": db_data,
    }
