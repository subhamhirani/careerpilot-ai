"""
CareerPilot AI — Agent 3: Job Matching Agent
============================================
Two-phase job matching pipeline:
  Phase 1 — Fast cosine-similarity filter (threshold > 0.35)
  Phase 2 — LLM-based detailed scoring across 7 weighted dimensions
             (skills, semantic, experience, location, tech stack,
              seniority, salary).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding Manager
# ---------------------------------------------------------------------------

class EmbeddingManager:
    """Generate and cache sentence-transformer embeddings.

    Uses the ``all-MiniLM-L6-v2`` model (384-dimensional, fast, good enough
    for semantic matching).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Any = None
        self._cache: dict[int, list[float]] = {}  # hash(text) -> vec

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers required. Install: pip install sentence-transformers"
                )
            logger.info("Loading embedding model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, text: str, normalize: bool = True) -> list[float]:
        """Encode a single text string to a 384-dim vector."""
        text_hash = hash(text)
        if text_hash in self._cache:
            return self._cache[text_hash]

        model = self._get_model()
        vec = model.encode(text, normalize_embeddings=normalize)
        result = vec.tolist()
        self._cache[text_hash] = result
        return result

    def encode_batch(
        self, texts: list[str], normalize: bool = True
    ) -> list[list[float]]:
        """Encode a batch of texts efficiently."""
        model = self._get_model()
        vecs = model.encode(texts, normalize_embeddings=normalize)
        results = []
        for i, text in enumerate(texts):
            result = vecs[i].tolist()
            self._cache[hash(text)] = result
            results.append(result)
        return results

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two normalized vectors.

        Since vectors are L2-normalized, this is just the dot product.
        """
        if len(a) != len(b):
            raise ValueError(f"Dimension mismatch: {len(a)} vs {len(b)}")
        dot = sum(x * y for x, y in zip(a, b))
        return float(dot)


# ---------------------------------------------------------------------------
# Match data models
# ---------------------------------------------------------------------------

@dataclass
class MatchScore:
    """Scoring breakdown for a single user-job pair."""
    user_id: str = ""
    job_hash_key: str = ""
    job_title: str = ""
    company: str = ""
    phase_1_similarity: float = 0.0
    # Phase-2 dimension scores (points)
    skills_score: float = 0.0       # max 30
    semantic_score: float = 0.0     # max 20
    experience_score: float = 0.0   # max 15
    location_score: float = 0.0     # max 15
    tech_stack_score: float = 0.0   # max 10
    seniority_score: float = 0.0    # max 5
    salary_score: float = 0.0       # max 5
    total_score: float = 0.0
    tier: str = ""                  # Excellent | Strong | Partial | Weak
    match_reason: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Tier thresholds
_TIER_THRESHOLDS = [
    ("Excellent", 85.0),  # 🟢
    ("Strong",    70.0),  # 🟡
    ("Partial",   50.0),  # 🟠
    ("Weak",       0.0),  # 🔴
]


def classify_tier(total_score: float) -> str:
    for tier, threshold in _TIER_THRESHOLDS:
        if total_score >= threshold:
            return tier
    return "Weak"


# ---------------------------------------------------------------------------
# Scoring prompt
# ---------------------------------------------------------------------------

_SCORING_SYSTEM_PROMPT = """\
You are an expert job-matching evaluator. Given a **user profile** and a **job posting**, score the match across 7 dimensions below.

Return ONLY a valid JSON object with this exact schema:
{
  "skills_score": 0.0,
  "semantic_score": 0.0,
  "experience_score": 0.0,
  "location_score": 0.0,
  "tech_stack_score": 0.0,
  "seniority_score": 0.0,
  "salary_score": 0.0,
  "match_reason": ""
}

**Dimension rules (total must not exceed max):**

1. **skills_score** (max 30 pts)
   - Count overlapping technical skills.
   - 0 pts = no overlap, 30 pts = nearly all required skills match.

2. **semantic_score** (max 20 pts)
   - How well the user's summary/experience aligns with the job description.
   - 0 = completely different domain; 20 = perfect domain alignment.

3. **experience_score** (max 15 pts)
   - Compare user's total_years_experience vs job's experience_required.
   - 15 = user exceeds requirement by 2+ yrs; 10 = meets it; 5 = close; 0 = far below.

4. **location_score** (max 15 pts)
   - 15 = exact location match; 10 = same city/region; 5 = same country; 0 = no overlap.
   - If the job is remote, default to 10 (remote is broadly accessible).

5. **tech_stack_score** (max 10 pts)
   - Overlap on specific technologies/tools/frameworks mentioned in the job.
   - 0 = none; 10 = user has used almost all mentioned tech.

6. **seniority_score** (max 5 pts)
   - Compare the user's current_role title level with the job's seniority.
   - 5 = exact seniority match; 3 = adjacent; 0 = mismatch.

7. **salary_score** (max 5 pts)
   - If salary data is available on both sides: 5 = within range; 3 = close; 0 = far off.
   - If salary data is missing: default to 2.5 (neutral).

8. **match_reason** — a concise, human-readable one-sentence explanation.

Be strict but fair. Use decimal precision for dimension scores.
"""


# ---------------------------------------------------------------------------
# JobMatcher
# ---------------------------------------------------------------------------

class JobMatcher:
    """Two-phase job matching engine.

    Phase 1 — fast cosine-similarity filter using embeddings.
    Phase 2 — detailed LLM-based scoring across 7 weighted dimensions.
    """

    def __init__(
        self,
        groq_api_key: str | None = None,
        groq_model: str = "llama-3.3-70b-versatile",
        embedding_model: str = "all-MiniLM-L6-v2",
        phase_1_threshold: float = 0.35,
    ) -> None:
        self.embedding_manager = EmbeddingManager(embedding_model)
        self.groq_api_key = groq_api_key
        self.groq_model = groq_model
        self.phase_1_threshold = phase_1_threshold
        self._groq_client: Any = None
        self._groq_available = True

    # ------------------------------------------------------------------
    # Phase 1 — Fast filter
    # ------------------------------------------------------------------

    def compute_similarity(
        self, profile_text: str, job_text: str
    ) -> float:
        """Cosine similarity between user profile and job posting."""
        emb_user = self.embedding_manager.encode(profile_text)
        emb_job = self.embedding_manager.encode(job_text)
        return self.embedding_manager.cosine_similarity(emb_user, emb_job)

    def fast_filter(
        self,
        profile_text: str,
        jobs: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], float]]:
        """Phase 1: return jobs with similarity > threshold, sorted desc."""
        candidates: list[tuple[dict[str, Any], float]] = []
        emb_user = self.embedding_manager.encode(profile_text)

        for job in jobs:
            job_text = self._job_text(job)
            emb_job = self.embedding_manager.encode(job_text)
            sim = self.embedding_manager.cosine_similarity(emb_user, emb_job)
            if sim >= self.phase_1_threshold:
                candidates.append((job, sim))

        candidates.sort(key=lambda x: x[1], reverse=True)
        logger.info(
            "Phase 1: %d / %d jobs passed threshold=%.2f",
            len(candidates),
            len(jobs),
            self.phase_1_threshold,
        )
        return candidates

    @staticmethod
    def _job_text(job: dict[str, Any]) -> str:
        """Concatenate job fields into a searchable text blob."""
        parts = [
            job.get("title", ""),
            job.get("company", ""),
            job.get("description", ""),
            job.get("location", ""),
            " ".join(job.get("skills", [])),
            job.get("employment_type", ""),
            job.get("work_mode", ""),
        ]
        return " ".join(p for p in parts if p)

    # ------------------------------------------------------------------
    # Phase 2 — Detailed LLM scoring
    # ------------------------------------------------------------------

    def _get_groq(self):
        if self._groq_client is not None:
            return self._groq_client
        if not self._groq_available:
            raise RuntimeError("Groq scoring unavailable (previous failure).")
        try:
            from groq import Groq as _Groq
        except ImportError:
            self._groq_available = False
            raise ImportError("groq package required for Phase 2 scoring.")

        key = self.groq_api_key
        if not key:
            import os
            key = os.environ.get("GROQ_API_KEY")
        if not key:
            self._groq_available = False
            raise ValueError("Groq API key required for Phase 2 scoring.")

        self._groq_client = _Groq(api_key=key)
        return self._groq_client

    def _build_user_context(self, profile: dict[str, Any]) -> str:
        """Format user profile for the scoring prompt."""
        lines = [
            f"Full Name: {profile.get('full_name', '')}",
            f"Current Role: {profile.get('current_role', '')}",
            f"Total Experience: {profile.get('total_years_experience', 0)} yrs",
            f"Skills: {', '.join(profile.get('skills', []))}",
            f"Soft Skills: {', '.join(profile.get('soft_skills', []))}",
            f"Preferred Locations: {', '.join(profile.get('preferred_locations', []))}",
            f"Employment Type: {profile.get('employment_type', '')}",
            f"Salary Expectation: {profile.get('salary_expectation', '')}",
            f"Target Roles: {', '.join(profile.get('target_roles', []))}",
            f"Summary: {profile.get('summary', '')}",
        ]
        # Work experience
        for i, exp in enumerate(profile.get("work_experience", []), 1):
            lines.append(
                f"Experience {i}: {exp.get('title', '')} @ {exp.get('company', '')} "
                f"({exp.get('start_date', '')} - {exp.get('end_date', '')})"
            )
            lines.append(f"  Technologies: {', '.join(exp.get('technologies', []))}")
            lines.append(f"  Description: {exp.get('description', '')[:200]}")
        # Education
        for edu in profile.get("education", []):
            lines.append(
                f"Education: {edu.get('degree', '')} in {edu.get('field', '')} "
                f"@ {edu.get('institution', '')}"
            )
        return "\n".join(lines)

    def _build_job_context(self, job: dict[str, Any]) -> str:
        """Format job posting for the scoring prompt."""
        lines = [
            f"Title: {job.get('title', '')}",
            f"Company: {job.get('company', '')}",
            f"Location: {job.get('location', '')}",
            f"Employment Type: {job.get('employment_type', '')}",
            f"Work Mode: {job.get('work_mode', '')}",
            f"Salary: {job.get('salary', '')}",
            f"Experience Required: {job.get('experience_required', '')}",
            f"Skills: {', '.join(job.get('skills', []))}",
            f"Description: {job.get('description', '')[:500]}",
        ]
        return "\n".join(lines)

    def score_job(
        self,
        profile: dict[str, Any],
        job: dict[str, Any],
        phase_1_similarity: float = 0.0,
    ) -> MatchScore:
        """Phase 2: detailed LLM-based scoring for one (profile, job) pair.

        Falls back to embedding-only scoring if Groq is unavailable.
        """
        # Determine if we can use Groq
        use_groq = True
        try:
            client = self._get_groq()
        except (ImportError, ValueError, RuntimeError):
            use_groq = False
            logger.warning("Groq unavailable; falling back to embedding-only scoring.")
            client = None

        user_context = self._build_user_context(profile)
        job_context = self._build_job_context(job)

        if use_groq and client is not None:
            try:
                result = self._groq_scoring(client, user_context, job_context)
            except Exception as exc:
                logger.warning("Groq scoring failed: %s. Falling back.", exc)
                result = self._embedding_fallback_scoring(profile, job)
        else:
            result = self._embedding_fallback_scoring(profile, job)

        # Build and return MatchScore
        total = (
            result.get("skills_score", 0)
            + result.get("semantic_score", 0)
            + result.get("experience_score", 0)
            + result.get("location_score", 0)
            + result.get("tech_stack_score", 0)
            + result.get("seniority_score", 0)
            + result.get("salary_score", 0)
        )

        return MatchScore(
            user_id=profile.get("full_name", "") or profile.get("email", ""),
            job_hash_key=job.get("hash_key", ""),
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            phase_1_similarity=phase_1_similarity,
            skills_score=result.get("skills_score", 0),
            semantic_score=result.get("semantic_score", 0),
            experience_score=result.get("experience_score", 0),
            location_score=result.get("location_score", 0),
            tech_stack_score=result.get("tech_stack_score", 0),
            seniority_score=result.get("seniority_score", 0),
            salary_score=result.get("salary_score", 0),
            total_score=total,
            tier=classify_tier(total),
            match_reason=result.get("match_reason", ""),
        )

    def _groq_scoring(
        self,
        client: Any,
        user_context: str,
        job_context: str,
    ) -> dict[str, Any]:
        """Call Groq LLM for detailed dimension scoring."""
        user_prompt = (
            "### User Profile ###\n"
            f"{user_context}\n\n"
            "### Job Posting ###\n"
            f"{job_context}\n\n"
            "Score this match following the dimension rules. "
            "Return ONLY the JSON object."
        )

        response = client.chat.completions.create(
            model=self.groq_model,
            messages=[
                {"role": "system", "content": _SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        # Strip any stray markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Groq returned invalid JSON. Using fallback.")
            return self._embedding_fallback_scoring(
                json.loads(user_context) if isinstance(user_context, str) else {},
                json.loads(job_context) if isinstance(job_context, str) else {},
            )

        # Ensure all keys exist
        defaults = {
            "skills_score": 0.0,
            "semantic_score": 0.0,
            "experience_score": 0.0,
            "location_score": 0.0,
            "tech_stack_score": 0.0,
            "seniority_score": 0.0,
            "salary_score": 0.0,
            "match_reason": "",
        }
        for k, v in defaults.items():
            data.setdefault(k, v)

        # Clamp to max values
        maxes = {
            "skills_score": 30,
            "semantic_score": 20,
            "experience_score": 15,
            "location_score": 15,
            "tech_stack_score": 10,
            "seniority_score": 5,
            "salary_score": 5,
        }
        for dim, mx in maxes.items():
            data[dim] = min(float(data.get(dim, 0)), mx)

        return data

    def _embedding_fallback_scoring(
        self,
        profile: dict[str, Any],
        job: dict[str, Any],
    ) -> dict[str, Any]:
        """Heuristic scoring based purely on embedding similarity and keyword overlap.

        Used when Groq is unavailable.
        """
        profile_text = self._build_user_context(profile)
        job_text = self._build_job_context(job)

        sim = self.compute_similarity(profile_text, job_text)

        # Skills overlap
        profile_skills = set(s.lower() for s in profile.get("skills", []))
        job_skills = set(s.lower() for s in job.get("skills", []))
        overlap = profile_skills & job_skills
        skills_score = min(30.0, (len(overlap) / max(len(job_skills), 1)) * 30) if job_skills else 15.0

        # Semantic = similarity scaled to 20
        semantic_score = min(20.0, sim * 20)

        # Experience heuristic
        user_exp = float(profile.get("total_years_experience", 0))
        job_exp_str = job.get("experience_required", "")
        job_exp = 0.0
        if job_exp_str:
            nums = re.findall(r"(\d+)", job_exp_str)
            if nums:
                job_exp = float(nums[0])
        exp_diff = user_exp - job_exp
        if exp_diff >= 2:
            experience_score = 15.0
        elif exp_diff >= 0:
            experience_score = 10.0
        elif exp_diff >= -1:
            experience_score = 5.0
        else:
            experience_score = 0.0

        # Location heuristic
        user_locs = [l.lower() for l in profile.get("preferred_locations", [])]
        job_loc = job.get("location", "").lower()
        work_mode = job.get("work_mode", "").lower()
        if work_mode == "remote":
            location_score = 10.0
        elif any(loc in job_loc or job_loc in loc for loc in user_locs):
            location_score = 15.0
        elif any(loc.split(",")[0].strip() in job_loc for loc in user_locs):
            location_score = 10.0
        elif user_locs and job_loc:
            location_score = 5.0
        else:
            location_score = 0.0

        # Tech stack / seniority / salary — use proportion of sim
        tech_stack_score = min(10.0, sim * 10)
        seniority_score = min(5.0, sim * 5)
        salary_score = 2.5  # neutral default

        total = (
            skills_score + semantic_score + experience_score
            + location_score + tech_stack_score + seniority_score + salary_score
        )

        return {
            "skills_score": skills_score,
            "semantic_score": semantic_score,
            "experience_score": experience_score,
            "location_score": location_score,
            "tech_stack_score": tech_stack_score,
            "seniority_score": seniority_score,
            "salary_score": salary_score,
            "match_reason": (
                f"Embedding similarity: {sim:.3f}. "
                f"Skills overlap: {len(overlap)}/{len(job_skills)}."
            ),
        }

    # ------------------------------------------------------------------
    # Batch matching
    # ------------------------------------------------------------------

    def match_all(
        self,
        profile: dict[str, Any],
        jobs: list[dict[str, Any]],
    ) -> list[MatchScore]:
        """Run Phase 1 + Phase 2 for a user against a list of jobs."""
        profile_text = self._build_user_context(profile)
        candidates = self.fast_filter(profile_text, jobs)

        results: list[MatchScore] = []
        for job, sim in candidates:
            score = self.score_job(profile, job, phase_1_similarity=sim)
            results.append(score)

        results.sort(key=lambda x: x.total_score, reverse=True)
        logger.info(
            "Matching complete: %d scores generated (tiers: %s)",
            len(results),
            {t: sum(1 for r in results if r.tier == t) for t in ["Excellent", "Strong", "Partial", "Weak"]},
        )
        return results


# ---------------------------------------------------------------------------
# Store match scores (asyncpg)
# ---------------------------------------------------------------------------

async def store_match_scores(
    scores: list[MatchScore],
    dsn: str | None = None,
) -> int:
    """Persist match scores to PostgreSQL.

    Returns the number of rows inserted.
    """
    import asyncpg

    if not dsn:
        import os
        dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        logger.warning("No DATABASE_URL set; scores will be logged but not stored.")
        for s in scores:
            logger.info("MATCH: %s | %.1f | %s", s.job_title, s.total_score, s.tier)
        return 0

    ddl = """
    CREATE TABLE IF NOT EXISTS careerpilot_match_scores (
        id              BIGSERIAL PRIMARY KEY,
        user_id         TEXT NOT NULL,
        job_hash_key    TEXT NOT NULL,
        job_title       TEXT NOT NULL,
        company         TEXT NOT NULL DEFAULT '',
        phase_1_similarity DOUBLE PRECISION DEFAULT 0.0,
        skills_score    DOUBLE PRECISION DEFAULT 0.0,
        semantic_score  DOUBLE PRECISION DEFAULT 0.0,
        experience_score DOUBLE PRECISION DEFAULT 0.0,
        location_score  DOUBLE PRECISION DEFAULT 0.0,
        tech_stack_score DOUBLE PRECISION DEFAULT 0.0,
        seniority_score DOUBLE PRECISION DEFAULT 0.0,
        salary_score    DOUBLE PRECISION DEFAULT 0.0,
        total_score     DOUBLE PRECISION DEFAULT 0.0,
        tier            TEXT NOT NULL DEFAULT 'Weak',
        match_reason    TEXT DEFAULT '',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, job_hash_key)
    );
    """

    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(ddl)
        count = 0
        for s in scores:
            try:
                await conn.execute(
                    """
                    INSERT INTO careerpilot_match_scores
                        (user_id, job_hash_key, job_title, company,
                         phase_1_similarity, skills_score, semantic_score,
                         experience_score, location_score, tech_stack_score,
                         seniority_score, salary_score, total_score, tier,
                         match_reason)
                    VALUES
                        ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (user_id, job_hash_key) DO UPDATE SET
                        total_score = EXCLUDED.total_score,
                        tier = EXCLUDED.tier,
                        match_reason = EXCLUDED.match_reason
                    """,
                    s.user_id, s.job_hash_key, s.job_title, s.company,
                    s.phase_1_similarity, s.skills_score, s.semantic_score,
                    s.experience_score, s.location_score, s.tech_stack_score,
                    s.seniority_score, s.salary_score, s.total_score, s.tier,
                    s.match_reason,
                )
                count += 1
            except Exception as exc:
                logger.warning("Failed to store score for %s: %s", s.job_hash_key, exc)
        return count
    finally:
        await conn.close()


def run_job_matching_task(
    profile: dict[str, Any],
    jobs: list[dict[str, Any]],
    dsn: str | None = None,
    groq_api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Synchronous entry point for running the full matching pipeline.

    Intended for use as a Celery task or direct call.
    Returns list of MatchScore dicts.
    """
    matcher = JobMatcher(groq_api_key=groq_api_key)
    scores = matcher.match_all(profile, jobs)

    # Write to DB if possible
    try:
        inserted = asyncio.run(store_match_scores(scores, dsn))
        logger.info("Stored %d match scores in database", inserted)
    except Exception as exc:
        logger.warning("Could not store scores in DB: %s", exc)

    return [s.to_dict() for s in scores]


# ---------------------------------------------------------------------------
# Celery task (conditional)
# ---------------------------------------------------------------------------

try:
    from celery import Celery as _Celery

    _celery_app = _Celery("careerpilot")
except ImportError:
    _celery_app = None

if _celery_app is not None:

    @_celery_app.task(
        bind=True,
        max_retries=3,
        default_retry_delay=30,
        autoretry_for=(Exception,),
    )
    def run_job_matching_celery_task(
        self,
        profile: dict[str, Any],
        jobs: list[dict[str, Any]],
        dsn: str | None = None,
        groq_api_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Celery task wrapper for run_job_matching_task."""
        return run_job_matching_task(profile, jobs, dsn, groq_api_key)
