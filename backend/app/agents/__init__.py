"""
CareerPilot AI — Agentic Layer
Agents 1-6: Resume Analysis, Job Discovery, Job Matching,
            Resume Tailoring, Cover Letter, Application
"""

from .resume_analysis import ResumeParser, UserProfile, extract_text_from_pdf, extract_text_from_docx
from .job_discovery import (
    BaseJobScraper,
    LinkedInScraper,
    NaukriScraper,
    IndeedIndiaScraper,
    RateLimiter,
    JobStorage,
    should_include_job,
    run_all_sources,
)
from .job_matching import EmbeddingManager, JobMatcher, run_job_matching_task, store_match_scores
from .resume_tailoring import (
    ResumeTailor,
    extract_nouns,
    safety_check,
    run_resume_tailoring_task,
)
from .cover_letter import CoverLetterGenerator, run_cover_letter_generation
from .application import ApplicationSubmitter, PendingApproval, run_application_submission
from .multi_agent_scoring import MultiAgentScorer, VectorSearchAgent, WebResearchAgent, SynthesisAgent

__all__ = [
    # Agent 1
    "ResumeParser",
    "UserProfile",
    "extract_text_from_pdf",
    "extract_text_from_docx",
    # Agent 2
    "BaseJobScraper",
    "LinkedInScraper",
    "NaukriScraper",
    "IndeedIndiaScraper",
    "RateLimiter",
    "JobStorage",
    "should_include_job",
    "run_all_sources",
    # Agent 3
    "EmbeddingManager",
    "JobMatcher",
    "run_job_matching_task",
    "store_match_scores",
    # Agent 4
    "ResumeTailor",
    "extract_nouns",
    "safety_check",
    "run_resume_tailoring_task",
    # Agent 5
    "CoverLetterGenerator",
    "run_cover_letter_generation",
    # Agent 6
    "ApplicationSubmitter",
    "PendingApproval",
    "run_application_submission",
    # Multi-Agent Scoring (P0)
    "MultiAgentScorer",
    "VectorSearchAgent",
    "WebResearchAgent",
    "SynthesisAgent",
]
