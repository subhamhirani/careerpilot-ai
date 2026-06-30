"""
CareerPilot AI — Multi-Agent Relevance Scoring
===============================================
Three specialized agents working in concert, inspired by the
agentic_rag_with_web_search pattern from awesome-ai-apps.

Pipeline:
  1. VectorSearchAgent   — semantic similarity via sentence-transformer embeddings
  2. WebResearchAgent    — company health signals from Wikipedia + web APIs
  3. SynthesisAgent      — Groq-powered synthesis of all signals into enriched scores

The output dict is a superset of the heuristic score_job() format used by
tasks_scraper.run_relevance_scoring, so it can be a drop-in replacement that
additionally provides company intelligence and natural-language reasoning.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_JOBS_FOR_LLM = 40        # top-N jobs that get the full LLM synthesis pass
_MAX_JOBS_FOR_WEB = 80       # top-N jobs whose companies get web research
_WEB_TIMEOUT_SEC = 6.0

# ---------------------------------------------------------------------------
# Agent 1 — Vector Search Agent
# ---------------------------------------------------------------------------

class VectorSearchAgent:
    """Compute embedding similarity and skill overlap against job postings.

    This is the "DB search" agent in the agentic-rag pipeline — it performs
    fast, local semantic matching without any external API call.
    """

    def __init__(self) -> None:
        self._embedding_manager: Any = None

    # ------------------------------------------------------------------
    # Lazy-loaded helpers
    # ------------------------------------------------------------------

    def _get_emb(self):
        if self._embedding_manager is None:
            from app.agents.job_matching import EmbeddingManager
            self._embedding_manager = EmbeddingManager()
        return self._embedding_manager

    @staticmethod
    def _build_profile_text(profile: dict) -> str:
        parts = [
            profile.get("summary", "") or "",
            " ".join(profile.get("skills", []) or []),
            " ".join(profile.get("preferred_roles", []) or []),
            " ".join(profile.get("preferred_locations", []) or []),
            str(profile.get("total_years_experience", profile.get("experience_years", 0))),
        ]
        return " ".join(p for p in parts if p)

    @staticmethod
    def _build_job_text(job: dict) -> str:
        parts = [
            job.get("title", "") or "",
            job.get("description", "") or "",
            job.get("location", "") or "",
            job.get("company", "") or "",
            " ".join(job.get("skills_required", job.get("skills", [])) or []),
        ]
        return " ".join(p for p in parts if p)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter_and_score(
        self,
        profile: dict,
        jobs: list[dict],
        threshold: float = 0.25,
    ) -> list[dict]:
        """Phase 1: fast semantic filter across all jobs.

        Returns scored job dicts (original job + vector_score), sorted
        by similarity descending.  Jobs below *threshold* are omitted.
        """
        emb = self._get_emb()
        profile_text = self._build_profile_text(profile)
        emb_user = emb.encode(profile_text)

        scored: list[dict] = []
        for job in jobs:
            job_text = self._build_job_text(job)
            emb_job = emb.encode(job_text)
            sim = emb.cosine_similarity(emb_user, emb_job)

            if sim >= threshold:
                # Also compute skill overlap
                matched, missing, ratio = self._match_skills(
                    profile.get("skills", []),
                    job_text,
                )
                scored.append({
                    **job,
                    "vector_score": round(sim, 4),
                    "skills_ratio": round(ratio, 3),
                    "matched_skills": matched,
                    "missing_skills": missing,
                })

        scored.sort(key=lambda j: j.get("vector_score", 0), reverse=True)
        logger.info(
            "VectorSearchAgent: %d / %d jobs passed threshold=%.2f",
            len(scored),
            len(jobs),
            threshold,
        )
        return scored

    @staticmethod
    def _match_skills(
        user_skills: list[str],
        job_text: str,
    ) -> tuple[list[str], list[str], float]:
        """Simple substring skill matching (no aliasing)."""
        job_lower = job_text.lower()
        matched = []
        missing = []
        for skill in user_skills:
            if skill.lower() in job_lower:
                matched.append(skill)
            else:
                missing.append(skill)
        ratio = len(matched) / max(len(user_skills), 1)
        return matched, missing, ratio


# ---------------------------------------------------------------------------
# Agent 2 — Web Research Agent
# ---------------------------------------------------------------------------

class WebResearchAgent:
    """Research companies by fetching public data from free web APIs.

    Uses Wikipedia and generic web-fetch to gather company signals:
    - description / industry
    - funding / notable milestones
    - recent news (headlines)
    - size / founded year
    """

    def __init__(self, timeout: float = _WEB_TIMEOUT_SEC) -> None:
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def research(self, company: str) -> dict:
        """Return a dict of company intelligence signals."""
        if not company or company.strip().lower() in ("unknown", "", "n/a"):
            return self._empty()

        result: dict[str, Any] = {
            "company": company,
            "summary": "",
            "founded_year": "",
            "industry": "",
            "headquarters": "",
            "signals": [],
        }

        # ── Try Wikipedia ──────────────────────────────────────────
        try:
            wiki = self._fetch_wikipedia(company)
            if wiki:
                result["summary"] = wiki.get("extract", "")[:600]
                result["founded_year"] = wiki.get("founded", "")
                result["industry"] = wiki.get("industry", "")
                result["headquarters"] = wiki.get("headquarters", "")
                if wiki.get("extract"):
                    result["signals"].append("has_wikipedia_page")
                    # Detect growth signals from summary text
                    summary_lower = (wiki.get("extract", "") or "").lower()
                    for kw, signal in [
                        ("acquired", "acquisition"),
                        ("funding", "funding_round"),
                        ("ipo", "publicly_traded"),
                        ("revenue", "revenue_growth"),
                        ("fortune", "fortune_listed"),
                        ("subsidiary", "backed_by_large_corp"),
                        ("startup", "startup"),
                    ]:
                        if kw in summary_lower:
                            result["signals"].append(signal)
        except Exception as exc:
            logger.debug("Wikipedia lookup failed for '%s': %s", company, exc)

        # ── Try a simple company-info API (Clearbit-style) ─────────
        if not result.get("signals"):
            # DuckDuckGo instant answer for a lightweight check
            try:
                ddg = self._fetch_ddg(company)
                if ddg:
                    result["summary"] = (result.get("summary", "") or "") + (
                        " | " + ddg[:400] if result.get("summary") else ddg[:400]
                    )
                    result["signals"].append("has_ddg_result")
            except Exception as exc:
                logger.debug("DDG lookup failed for '%s': %s", company, exc)

        return result

    def research_batch(self, companies: list[str]) -> dict[str, dict]:
        """Deduplicated research for a list of company names."""
        seen: set[str] = set()
        results: dict[str, dict] = {}
        for c in companies:
            key = c.strip().lower()
            if key and key not in seen and key not in ("unknown", "", "n/a"):
                seen.add(key)
                try:
                    results[c] = self.research(c)
                except Exception as exc:
                    logger.warning("Research failed for '%s': %s", c, exc)
                    results[c] = self._empty()
        return results

    # ------------------------------------------------------------------
    # Internal fetchers
    # ------------------------------------------------------------------

    def _fetch_wikipedia(self, company: str) -> dict:
        """Fetch company info from Wikipedia REST API."""
        # Normalise: "Amazon Web Services" -> "Amazon_(company)"
        # We try the raw name first, then with "(company)" suffix
        candidates = [company, f"{company} (company)", f"{company} (software)"]

        for name in candidates:
            url = (
                "https://en.wikipedia.org/api/rest_v1/page/summary/"
                + quote(name.replace(" ", "_"))
            )
            resp = self._client.get(url, headers={"User-Agent": "CareerPilot/1.0"})
            if resp.status_code != 200:
                continue

            data = resp.json()
            if data.get("type") == "disambiguation":
                continue  # skip disambiguation pages

            extract = data.get("extract", "") or ""

            # Parse infobox-like data from the extract
            result: dict[str, Any] = {
                "extract": extract,
                "founded": "",
                "industry": "",
                "headquarters": "",
            }

            # Try to extract structured data from first paragraph
            text_lower = extract.lower()
            # Founded year
            fy = re.search(r"founded in (\d{4})", text_lower)
            if fy:
                result["founded"] = fy.group(1)
            # Headquarters
            hq = re.search(r"headquartered in ([A-Z][a-z]+[^,]*?)(?:,|\.|and)", extract)
            if hq:
                result["headquarters"] = hq.group(1).strip()
            # Industry
            ind = re.search(r"is an? (american|indian|british|global) ([\w\s]+?) company", text_lower)
            if ind:
                result["industry"] = ind.group(2).strip()

            return result

        return {}

    def _fetch_ddg(self, query: str) -> str:
        """DuckDuckGo instant answer — lightweight, no API key."""
        url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
        resp = self._client.get(url, headers={"User-Agent": "CareerPilot/1.0"})
        if resp.status_code != 200:
            return ""

        data = resp.json()
        # Try Abstract first, then Answer, then Definition
        for field in ("AbstractText", "Answer", "Definition"):
            val = (data.get(field) or "").strip()
            if val:
                return val[:500]
        return ""

    @staticmethod
    def _empty() -> dict:
        return {"company": "", "summary": "", "founded_year": "",
                "industry": "", "headquarters": "", "signals": []}

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Agent 3 — Synthesis Agent
# ---------------------------------------------------------------------------

class SynthesisAgent:
    """LLM-powered synthesis of vector scores + company research + job data.

    Uses the existing query_llm() abstraction (with Groq → Gemini fallback)
    to produce a final enriched match score with human-readable reasoning.
    """

    _SYSTEM_PROMPT = """\
You are an expert job-match evaluator with access to three signals:
1. **Vector similarity** — semantic closeness of the user's profile to the job.
2. **Company research** — Wikipedia / web data about the employer.
3. **Skill overlap** — which user skills match or are missing from the job.

Score the match across **6 dimensions** (each 0-100):

| Dimension          | Weight | Description                                      |
|--------------------|--------|--------------------------------------------------|
| skills_align       | 30%    | How well the user's skills match job requirements |
| experience_fit     | 20%    | Years of experience vs what the job asks for      |
| location_fit       | 15%    | Geographic match (remote, same city, state...)    |
| role_alignment     | 20%    | Does the job title align with the user's target?  |
| company_health     | 10%    | Company stability, growth signals, reputation     |
| growth_potential   | 5%     | Does this role offer career growth for the user?  |

Return ONLY a valid JSON object with this exact schema:
{
  "skills_align": 0-100,
  "experience_fit": 0-100,
  "location_fit": 0-100,
  "role_alignment": 0-100,
  "company_health": 0-100,
  "growth_potential": 0-100,
  "match_reason": "one sentence why this is a good/bad match"
}

Rules:
- Be strict — a mediocre match should get mediocre scores.
- company_health of 50 is "neutral" (company not researched).
- match_reason must be 1-2 sentences, human-readable.
"""

    def synthesize(
        self,
        profile: dict,
        job: dict,
        vector_data: dict,
        company_data: dict,
    ) -> dict:
        """Synthesise all signals into a single enriched score dict.

        The returned dict matches the *score_job()* output shape so it
        can be slotted directly into match_scores rows.
        """
        # Build the prompt
        user_context = self._user_context(profile)
        job_context = self._job_context(job)
        signals = self._signal_context(vector_data, company_data)

        prompt = f"""\
### User Profile ###
{user_context}

### Job Posting ###
{job_context}

### Agent Signals ###
{signals}

Based on the above, score the match across all 6 dimensions.
Return ONLY the JSON object."""

        # Call LLM
        raw = self._call_llm(prompt)
        dims = self._parse_response(raw)
        if dims is None:
            # Fallback: use vector-only heuristic
            logger.warning("SynthesisAgent: LLM returned invalid JSON, using fallback")
            dims = self._fallback(vector_data, company_data, job)

        # Convert to score_job()-compatible output
        return {
            "total_score": round(
                dims["skills_align"] * 0.30
                + dims["experience_fit"] * 0.20
                + dims["location_fit"] * 0.15
                + dims["role_alignment"] * 0.20
                + dims["company_health"] * 0.10
                + dims["growth_potential"] * 0.05,
                1,
            ),
            "skills_score": round(dims["skills_align"] * 0.30, 1),
            "experience_score": round(dims["experience_fit"] * 0.20, 1),
            "location_score": round(dims["location_fit"] * 0.15, 1),
            "role_score": round(dims["role_alignment"] * 0.20, 1),
            "company_health_score": round(dims["company_health"] * 0.10, 1),
            "growth_alignment_score": round(dims["growth_potential"] * 0.05, 1),
            "matched_skills": vector_data.get("matched_skills", []),
            "missing_skills": vector_data.get("missing_skills", []),
            "company_summary": (company_data or {}).get("summary", "")[:300],
            "match_reason": dims.get("match_reason", ""),
            "grade": self._grade_from_score(
                dims["skills_align"] * 0.30
                + dims["experience_fit"] * 0.20
                + dims["location_fit"] * 0.15
                + dims["role_alignment"] * 0.20
                + dims["company_health"] * 0.10
                + dims["growth_potential"] * 0.05,
            ),
        }

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _user_context(profile: dict) -> str:
        lines = [
            f"Name: {profile.get('full_name', '') or profile.get('name', '')}",
            f"Summary: {(profile.get('summary', '') or '')[:300]}",
            f"Skills: {', '.join(profile.get('skills', []) or [])}",
            f"Experience: {profile.get('total_years_experience', profile.get('experience_years', 0))} yrs",
            f"Target Roles: {', '.join(profile.get('preferred_roles', []) or [])}",
            f"Preferred Locations: {', '.join(profile.get('preferred_locations', []) or [])}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _job_context(job: dict) -> str:
        lines = [
            f"Title: {job.get('title', '')}",
            f"Company: {job.get('company', '')}",
            f"Location: {job.get('location', '')}",
            f"Type: {job.get('employment_type', '') or job.get('work_mode', '')}",
            f"Experience Required: {job.get('experience_required', '') or job.get('exp_required', '')}",
            f"Description: {(job.get('description', '') or '')[:400]}",
        ]
        skills = job.get("skills_required", job.get("skills", []))
        if skills:
            lines.append(f"   Skills: {', '.join(skills[:10])}")
        return "\n".join(lines)

    @staticmethod
    def _signal_context(vector_data: dict, company_data: dict | None) -> str:
        lines = [
            f"Vector similarity: {vector_data.get('vector_score', 0.5)}",
            f"Skill match ratio: {vector_data.get('skills_ratio', 0)}",
            f"Matched skills: {', '.join(vector_data.get('matched_skills', [])[:8])}",
            f"Missing skills: {', '.join(vector_data.get('missing_skills', [])[:5])}",
        ]
        if company_data and company_data.get("signals"):
            cd = company_data
            lines.append(f"Company summary: {(cd.get('summary', '') or '')[:300]}")
            lines.append(f"Founded: {cd.get('founded_year', 'unknown')}")
            lines.append(f"Industry: {cd.get('industry', 'unknown')}")
            lines.append(f"Signals: {', '.join(cd.get('signals', []))}")
        else:
            lines.append("Company research: unavailable")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    @staticmethod
    def _call_llm(prompt: str) -> str:
        """Call query_llm with a system prompt, handle failures."""
        try:
            from app.llm_client import query_llm
            return query_llm(
                prompt=prompt,
                system_prompt=SynthesisAgent._SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception as exc:
            logger.warning("SynthesisAgent: LLM call failed: %s", exc)
            return ""

    @staticmethod
    def _parse_response(raw: str) -> dict | None:
        """Parse the LLM JSON response, cleaning markdown fences."""
        if not raw.strip():
            return None
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        required = [
            "skills_align", "experience_fit", "location_fit",
            "role_alignment", "company_health", "growth_potential",
        ]
        for key in required:
            if key not in data:
                return None
            data[key] = min(float(data[key]), 100.0)

        data.setdefault("match_reason", "")
        return data

    @staticmethod
    def _fallback(vector_data: dict, company_data: dict | None, job: dict) -> dict:
        """Heuristic fallback when the LLM call fails."""
        vs = vector_data.get("vector_score", 0.5) or 0.5
        sr = vector_data.get("skills_ratio", 0) or 0
        ch = 50  # neutral company health

        signals = (company_data or {}).get("signals", [])
        if any(s in ("publicly_traded", "revenue_growth", "acquisition") for s in signals):
            ch = 70
        elif any(s in ("backed_by_large_corp", "fortune_listed") for s in signals):
            ch = 65
        elif "startup" in signals:
            ch = 40

        return {
            "skills_align": min(100, sr * 100),
            "experience_fit": min(100, vs * 80 + 20),
            "location_fit": 60,
            "role_alignment": min(100, vs * 90 + 10),
            "company_health": ch,
            "growth_potential": min(100, 30 + vs * 30),
            "match_reason": f"Similarity {vs:.2f}, skill match {sr:.0%}, company research {'available' if signals else 'not available'}.",
        }

    @staticmethod
    def _grade_from_score(score: float) -> str:
        if score >= 80:
            return "EXCELLENT"
        elif score >= 60:
            return "GOOD"
        elif score >= 40:
            return "FAIR"
        return "POOR"


# ---------------------------------------------------------------------------
# Orchestrator — ties the three agents together
# ---------------------------------------------------------------------------

class MultiAgentScorer:
    """Orchestrator that runs the three-agent pipeline end-to-end.

    Usage::

        scorer = MultiAgentScorer()
        scores = scorer.score_all(profile_dict, job_dicts)

    Each element in *scores* is a dict compatible with the existing
    ``score_job()`` output format, plus extra fields (company_summary,
    growth_alignment_score, match_reason) that are stored in the
    match_scores ``details`` JSONB column.
    """

    def __init__(self) -> None:
        self._vector_agent: VectorSearchAgent | None = None
        self._web_agent: WebResearchAgent | None = None
        self._synthesis_agent: SynthesisAgent | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_all(
        self,
        profile: dict,
        jobs: list[dict],
        phase_1_threshold: float = 0.25,
    ) -> list[dict]:
        """Run the full three-agent pipeline.

        Steps:
          1. VectorSearchAgent — fast semantic filter and skill matching
          2. WebResearchAgent — company research for top-N unique employers
          3. SynthesisAgent — LLM scoring for top-M jobs

        Returns scored job dicts sorted by total_score descending.
        """
        logger.info("MultiAgentScorer: scoring %d jobs for profile", len(jobs))

        # ── Phase 1: Vector search + skill matching ────────────────
        vector = self._get_vector_agent()
        scored = vector.filter_and_score(profile, jobs, threshold=phase_1_threshold)

        if not scored:
            logger.info("MultiAgentScorer: no jobs passed phase 1 threshold")
            return []

        # ── Phase 2: Web research for unique companies (top N) ────
        top_for_web = scored[:_MAX_JOBS_FOR_WEB]
        companies = list(dict.fromkeys(j.get("company", "") for j in top_for_web if j.get("company")))
        company_data: dict[str, dict] = {}
        if companies:
            web = self._get_web_agent()
            try:
                company_data = web.research_batch(companies)
            finally:
                web.close()

        # ── Phase 3: LLM synthesis for top M jobs ─────────────────
        synthesis = self._get_synthesis_agent()
        results: list[dict] = []
        for job in scored[:_MAX_JOBS_FOR_LLM]:
            vector_data = {
                "vector_score": job.get("vector_score", 0.5),
                "skills_ratio": job.get("skills_ratio", 0),
                "matched_skills": job.get("matched_skills", []),
                "missing_skills": job.get("missing_skills", []),
            }
            cd = company_data.get(job.get("company", ""), {})
            enriched = synthesis.synthesize(profile, job, vector_data, cd)
            results.append({
                **job,
                **enriched,
            })

        # For jobs beyond the LLM cap, use heuristic-only scoring
        for job in scored[_MAX_JOBS_FOR_LLM:]:
            results.append({
                **job,
                "total_score": round(
                    (job.get("vector_score", 0) or 0) * 50
                    + (job.get("skills_ratio", 0) or 0) * 50,
                    1,
                ),
                "skills_score": round((job.get("skills_ratio", 0) or 0) * 30, 1),
                "experience_score": 10.0,
                "location_score": 7.5,
                "role_score": round((job.get("vector_score", 0) or 0) * 20, 1),
                "company_health_score": 5.0,
                "growth_alignment_score": 2.5,
                "matched_skills": job.get("matched_skills", []),
                "missing_skills": job.get("missing_skills", []),
                "company_summary": "",
                "match_reason": "Lower-priority match (vector-only scoring).",
                "grade": "FAIR",
            })

        # Sort by total_score descending
        results.sort(key=lambda r: r.get("total_score", 0), reverse=True)
        logger.info("MultiAgentScorer: generated %d enriched scores", len(results))
        return results

    # ------------------------------------------------------------------
    # Lazy agent getters
    # ------------------------------------------------------------------

    def _get_vector_agent(self) -> VectorSearchAgent:
        if self._vector_agent is None:
            self._vector_agent = VectorSearchAgent()
        return self._vector_agent

    def _get_web_agent(self) -> WebResearchAgent:
        if self._web_agent is None:
            self._web_agent = WebResearchAgent()
        return self._web_agent

    def _get_synthesis_agent(self) -> SynthesisAgent:
        if self._synthesis_agent is None:
            self._synthesis_agent = SynthesisAgent()
        return self._synthesis_agent
