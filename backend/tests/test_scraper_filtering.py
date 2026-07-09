"""
Unit tests for job scraper query building and criteria filtering.
Validates that job scraping prioritizes the first job title and then skills,
and filters out non-matching random jobs.
"""
from __future__ import annotations

from app.tasks_scraper import _matches_user_criteria


def test_matches_user_criteria_first_job_title_match():
    first_job_title = "Software Engineer"
    skills = ["Python", "Docker"]

    matching_job = {
        "title": "Senior Software Engineer - Python",
        "description": "We are looking for a Python developer with Docker skills.",
        "skills": ["Python", "Docker"],
    }
    assert _matches_user_criteria(matching_job, first_job_title, skills) is True


def test_matches_user_criteria_rejects_random_job_title():
    first_job_title = "Software Engineer"
    skills = ["Python", "Docker"]

    random_job = {
        "title": "HR Manager",
        "description": "Recruiting Python developers for our team.",
        "skills": ["Python"],
    }
    # Even though description contains 'Python', the title 'HR Manager' does not match Software Engineer
    assert _matches_user_criteria(random_job, first_job_title, skills) is False


def test_matches_user_criteria_rejects_job_without_skills():
    first_job_title = "Software Engineer"
    skills = ["React", "TypeScript"]

    unskilled_job = {
        "title": "Software Engineer",
        "description": "Looking for a C++ developer with kernel programming experience.",
        "skills": ["C++", "Linux"],
    }
    assert _matches_user_criteria(unskilled_job, first_job_title, skills) is False


def test_matches_user_criteria_no_criteria():
    job = {"title": "Any Job", "description": "Anything"}
    assert _matches_user_criteria(job, None, []) is True
