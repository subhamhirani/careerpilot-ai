"""
CareerPilot AI — Cover Letter Generator
=========================================
Template-based cover letter generation.
Uses user profile + job details to create personalized letters.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def generate_cover_letter(profile: dict, job: dict) -> str:
    """Generate a personalized cover letter.

    Args:
        profile: User profile dict with keys: full_name, skills, experience_years,
                 summary, preferred_roles, preferred_locations
        job: Job posting dict with keys: title, company, location, description,
             skills, experience_required, employment_type

    Returns:
        Cover letter text (string).
    """
    name = profile.get("full_name", "Candidate")
    skills = profile.get("skills", [])
    exp_years = profile.get("experience_years", 0)
    summary = profile.get("summary", "")
    preferred_roles = profile.get("preferred_roles", [])
    locations = profile.get("preferred_locations", [])

    job_title = job.get("title", "the position")
    job_company = job.get("company", "your company")
    job_location = job.get("location", "")
    job_desc = job.get("description", "")
    job_skills = job.get("skills", [])
    job_exp = job.get("experience_required", "")

    # Find matching skills
    job_text = f"{job_title} {job_desc} {' '.join(job_skills)}".lower()
    matched = []
    for skill in skills:
        if skill.lower() in job_text:
            matched.append(skill)

    # Build experience sentence
    if exp_years >= 1:
        exp_str = f"With {exp_years}+ year{'s' if exp_years > 1 else ''} of hands-on experience"
    else:
        exp_str = "With strong foundational experience"

    # Build skills sentence
    if matched:
        top_skills = matched[:5]
        skills_str = ", ".join(top_skills)
        skills_sentence = f"My core competencies include {skills_str}, which align directly with this role's requirements."
    elif skills:
        skills_str = ", ".join(skills[:5])
        skills_sentence = f"My technical toolkit includes {skills_str}."
    else:
        skills_sentence = ""

    # Build role alignment
    role_section = ""
    if preferred_roles:
        role_section = f"I am actively seeking {' and '.join(preferred_roles[:2])} opportunities. "

    # Build location sentence
    loc_str = ""
    if locations:
        loc_str = f"Based in {locations[0]}, "

    # Generate the letter
    letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {job_company}. {exp_str} in network engineering, infrastructure management, and cybersecurity, I am confident I can contribute meaningfully to your team.

{skills_sentence}

Throughout my career, I have:
- Deployed and managed Windows Server environments with Active Directory, DNS, DHCP, and Group Policy administration
- Built and maintained automated backup and disaster recovery systems for business-critical data
- Configured multi-ISP redundant networks and hardened infrastructure against security threats
- Worked extensively with Docker containers, Linux administration, and AWS cloud services

{role_section}{loc_str}and I am excited about the opportunity to bring my infrastructure expertise to {job_company}.

{job_company}'s reputation for {'technical excellence and innovation' if not job_desc else 'its work in the industry'} resonates with my professional values. {'The role particularly appeals to me because ' + job_desc[:100] if job_desc else 'I believe my background makes me a strong fit for this position.'}

I would welcome the opportunity to discuss how my skills and experience can contribute to {job_company}'s continued success. Thank you for your time and consideration.

Best regards,
{name}
{', '.join(locations) if locations else 'India'}
"""

    return letter


def generate_cover_letter_short(profile: dict, job: dict) -> str:
    """Generate a shorter cover letter (for quick apply)."""
    name = profile.get("full_name", "Candidate")
    skills = profile.get("skills", [])
    exp_years = profile.get("experience_years", 0)

    job_title = job.get("title", "the position")
    job_company = job.get("company", "your company")

    job_text = f"{job_title} {job.get('description', '')} {' '.join(job.get('skills', []))}".lower()
    matched = [s for s in skills if s.lower() in job_text][:3]

    skills_line = f" My expertise in {', '.join(matched)} aligns well with your requirements." if matched else ""

    letter = f"""Hi,

I'm interested in the {job_title} role at {job_company}.{skills_line} With {exp_years}+ year{'s' if exp_years > 1 else ''} of experience in infrastructure and security, I'm eager to contribute to your team.

Best,
{name}
"""
    return letter
