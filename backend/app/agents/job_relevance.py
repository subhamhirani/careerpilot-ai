"""
CareerPilot AI — Job Relevance Scoring Engine
==============================================
Scores job postings against a user's resume profile.
Uses keyword matching, experience fit, location, and role alignment.
No external ML dependencies — pure Python.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User Profile model
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    """Simplified user profile for relevance scoring."""
    full_name: str = ""
    skills: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    preferred_locations: list[str] = field(default_factory=list)
    target_roles: list[str] = field(default_factory=list)
    summary: str = ""
    preferred_employment_type: str = ""


# ---------------------------------------------------------------------------
# Skill matching
# ---------------------------------------------------------------------------

# Normalisation map for common skill variations
_SKILL_ALIASES: dict[str, list[str]] = {
    "tcp/ip": ["tcp/ip", "tcpip", "tcp ip"],
    "dns": ["dns", "domain name system"],
    "dhcp": ["dhcp", "dynamic host configuration"],
    "vlan": ["vlan", "virtual lan"],
    "ospf": ["ospf", "open shortest path first"],
    "nat": ["nat", "network address translation"],
    "pat": ["pat", "port address translation"],
    "vpn": ["vpn", "virtual private network"],
    "wireshark": ["wireshark", "packet capture", "packet analysis"],
    "wazuh": ["wazuh", "siem", "security information"],
    "active directory": ["active directory", "ad ds", "ad", "directory services"],
    "group policy": ["group policy", "gpo", "group policy object"],
    "windows server": ["windows server", "win server", "windows server 2025", "windows server 2022"],
    "docker": ["docker", "container", "containerisation", "containerization"],
    "aws": ["aws", "amazon web services", "ec2", "vpc", "iam", "s3"],
    "linux": ["linux", "ubuntu", "centos", "rhel", "red hat"],
    "git": ["git", "github", "gitlab"],
    "powershell": ["powershell", "ps", "power shell"],
    "python": ["python", "python3"],
    "java": ["java", "jdk"],
    "javascript": ["javascript", "js", "node.js", "nodejs"],
    "typescript": ["typescript", "ts"],
    "react": ["react", "reactjs"],
    "angular": ["angular", "angularjs"],
    "sql": ["sql", "mysql", "postgresql", "postgres"],
    "terraform": ["terraform", "iac", "infrastructure as code"],
    "kubernetes": ["kubernetes", "k8s"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins", "ci/cd", "cicd"],
    "prometheus": ["prometheus", "grafana", "monitoring"],
    "cybersecurity": ["cybersecurity", "cyber security", "security", "infosec"],
    "soc": ["soc", "security operations", "soc analyst", "security analyst"],
    "incident response": ["incident response", "incident handling", "ir"],
    "firewall": ["firewall", "firewalling", "palo alto", "fortinet"],
    "networking": ["networking", "network", "lan", "wan", "routing", "switching"],
    "cloud": ["cloud", "cloud computing", "cloud engineer"],
    "devops": ["devops", "dev ops", "sre", "site reliability"],
    "system administration": ["system administration", "sysadmin", "system admin", "administrator"],
}


def _normalise_skill(skill: str) -> set[str]:
    """Return the set of canonical forms for a skill."""
    skill_lower = skill.lower().strip()
    result = {skill_lower}
    for canonical, aliases in _SKILL_ALIASES.items():
        if skill_lower in aliases or skill_lower == canonical:
            result.add(canonical)
            result.update(aliases)
    return result


def _match_skills(user_skills: list[str], job_text: str) -> tuple[list[str], list[str], float]:
    """Match user skills against job text.

    Returns (matched_skills, missing_skills, match_ratio).
    """
    job_lower = job_text.lower()
    matched = []
    missing = []

    for skill in user_skills:
        variants = _normalise_skill(skill)
        found = any(v in job_lower for v in variants)
        if found:
            matched.append(skill)
        else:
            missing.append(skill)

    ratio = len(matched) / max(len(user_skills), 1)
    return matched, missing, ratio


# ---------------------------------------------------------------------------
# Experience scoring
# ---------------------------------------------------------------------------

def _parse_experience_years(exp_str: str) -> tuple[float, float]:
    """Parse experience string like '3-5 years' into (min, max)."""
    if not exp_str:
        return (0, 0)

    text = exp_str.lower().strip()
    numbers = re.findall(r"(\d+)", text)

    if not numbers:
        return (0, 0)

    if len(numbers) >= 2:
        return (float(numbers[0]), float(numbers[1]))
    else:
        n = float(numbers[0])
        # "3+ years" -> (3, 10)
        if "+" in text:
            return (n, 10)
        # "3 years" -> (0, 3)
        return (0, n)


def _score_experience(user_years: float, job_exp_str: str) -> float:
    """Score experience fit (0-100)."""
    if not job_exp_str:
        return 70.0  # No requirement = neutral

    min_exp, max_exp = _parse_experience_years(job_exp_str)

    if min_exp == 0 and max_exp == 0:
        return 70.0

    if user_years < min_exp:
        # Under-qualified
        gap = min_exp - user_years
        if gap <= 1:
            return 60.0
        elif gap <= 2:
            return 40.0
        else:
            return 20.0
    elif user_years >= min_exp and user_years <= max_exp + 2:
        # Within or slightly above range = perfect
        return 100.0
    else:
        # Over-qualified
        return 75.0


# ---------------------------------------------------------------------------
# Location scoring
# ---------------------------------------------------------------------------

def _score_location(user_locations: list[str], job_location: str) -> float:
    """Score location match (0-100)."""
    if not job_location:
        return 50.0

    job_loc = job_location.lower().strip()

    # Check for remote
    if "remote" in job_loc or "work from home" in job_loc or "wfh" in job_loc:
        return 85.0

    for user_loc in user_locations:
        user_lower = user_loc.lower().strip()
        if not user_lower:
            continue
        # Exact match
        if user_lower in job_loc or job_loc in user_lower:
            return 100.0
        # City match (e.g., "ahmedabad" in "ahmedabad, gujarat, india")
        if user_lower in job_loc:
            return 100.0
        # State match
        user_parts = set(user_lower.replace(",", " ").split())
        job_parts = set(job_loc.replace(",", " ").split())
        if user_parts & job_parts:
            return 70.0

    # Country match (India)
    if "india" in job_loc:
        return 40.0

    return 20.0


# ---------------------------------------------------------------------------
# Role alignment scoring
# ---------------------------------------------------------------------------

def _score_role_alignment(target_roles: list[str], job_title: str) -> float:
    """Score how well the job title matches target roles (0-100)."""
    if not target_roles or not job_title:
        return 50.0

    title_lower = job_title.lower()
    best_score = 0.0

    for role in target_roles:
        role_lower = role.lower().strip()
        if not role_lower:
            continue

        # Exact match
        if role_lower in title_lower:
            best_score = max(best_score, 100.0)
            continue

        # Partial word match
        role_words = set(role_lower.split())
        title_words = set(title_lower.split())
        overlap = role_words & title_words
        if overlap:
            score = (len(overlap) / len(role_words)) * 80.0
            best_score = max(best_score, score)

    return best_score


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_job(profile: UserProfile, job: dict) -> dict[str, Any]:
    """Score a single job against a user profile.

    Args:
        profile: UserProfile with resume data
        job: JobPosting dict (from multi_portal_scraper)

    Returns:
        Dict with scoring breakdown and total.
    """
    # Build searchable job text
    job_text = " ".join([
        job.get("title", "") or "",
        job.get("description", "") or "",
        job.get("location", "") or "",
    ])

    # 1. Skills match (weight: 40%)
    matched_skills, missing_skills, skills_ratio = _match_skills(profile.skills, job_text)
    skills_score = skills_ratio * 100

    # 2. Experience fit (weight: 20%)
    exp_score = _score_experience(profile.experience_years, job.get("experience_required", "") or "")

    # 3. Location match (weight: 15%)
    loc_score = _score_location(profile.preferred_locations, job.get("location", "") or "")

    # 4. Role alignment (weight: 25%)
    role_score = _score_role_alignment(profile.target_roles, job.get("title", ""))

    # Weighted total
    total = (
        skills_score * 0.40
        + exp_score * 0.20
        + loc_score * 0.15
        + role_score * 0.25
    )

    return {
        "total_score": round(total, 1),
        "skills_score": round(skills_score, 1),
        "experience_score": round(exp_score, 1),
        "location_score": round(loc_score, 1),
        "role_score": round(role_score, 1),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }


def rank_jobs(profile: UserProfile, jobs: list[dict]) -> list[dict]:
    """Score and rank jobs by relevance (descending)."""
    for job in jobs:
        job["relevance"] = score_job(profile, job)
    jobs.sort(key=lambda j: j["relevance"]["total_score"], reverse=True)
    return jobs


def filter_relevant(jobs: list[dict], min_score: float = 35.0) -> list[dict]:
    """Return only jobs above the relevance threshold."""
    return [j for j in jobs if j.get("relevance", {}).get("total_score", 0) >= min_score]


# ---------------------------------------------------------------------------
# Convenience: build profile from resume dict
# ---------------------------------------------------------------------------

def profile_from_resume(resume_text: str) -> UserProfile:
    """Build a UserProfile from raw resume text (heuristic extraction)."""
    profile = UserProfile()

    # Extract name (first line)
    lines = [l.strip() for l in resume_text.strip().split('\n') if l.strip()]
    if lines:
        profile.full_name = lines[0]

    # Extract skills from the TECHNICAL SKILLS section
    skills_section = re.search(r'TECHNICAL SKILLS(.*?)(?:\nEDUCATION|\nTRAINING)', resume_text, re.DOTALL)
    if skills_section:
        skills_text = skills_section.group(1)
        current_category = ""
        for line in skills_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('Currently'):
                continue
            # Detect category headers (e.g., "Networking:", "Security & SOC:")
            if line.endswith(':') and len(line) < 40:
                current_category = line.rstrip(':')
                continue
            # Remove category prefix if present (e.g., "Networking: TCP/IP")
            if ':' in line and len(line.split(':')[0]) < 30:
                line = line.split(':', 1)[1].strip()
            # Split by bullet points and colons
            parts = re.split(r'[·▸•]', line)
            for part in parts:
                part = part.strip().strip(':').strip()
                if part and len(part) < 50 and len(part) > 1:
                    for skill in part.split(','):
                        skill = skill.strip().strip('-').strip()
                        if skill and len(skill) > 1 and not skill.startswith('Currently'):
                            if skill not in profile.skills:
                                profile.skills.append(skill)

    # Also extract from experience descriptions
    exp_section = re.search(r'EXPERIENCE(.*?)(?:\nPROJECTS|\nOPEN TO)', resume_text, re.DOTALL)
    if exp_section:
        exp_text = exp_section.group(1)
        tech_keywords = [
            'TCP/IP', 'DNS', 'DHCP', 'VLAN', 'OSPF', 'NAT', 'PAT', 'VPN',
            'Wireshark', 'Wazuh', 'SIEM', 'firewall', 'Active Directory',
            'Group Policy', 'GPO', 'Windows Server', 'Docker', 'Linux',
            'AWS', 'EC2', 'VPC', 'IAM', 'S3', 'Hyper-V', 'PowerShell',
            'Git', 'GitHub', 'GitLab', 'Python', 'Bash', 'Restic',
            'Ubuntu', 'CentOS', 'RHEL', 'FTP', 'SFTP', 'IIS',
        ]
        for kw in tech_keywords:
            if kw.lower() in exp_text.lower() and kw not in profile.skills:
                profile.skills.append(kw)

    # Extract years of experience
    exp_match = re.search(r'(\d+)\+?\s*year', resume_text.lower())
    if exp_match:
        profile.experience_years = float(exp_match.group(1))

    # Extract location
    loc_match = re.search(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s*India', resume_text)
    if loc_match:
        profile.preferred_locations.append(loc_match.group(1))

    # Target roles
    open_to = re.search(r'OPEN TO(.*?)(?:\n\n)', resume_text, re.DOTALL)
    if open_to:
        for line in open_to.group(1).split('\n'):
            line = line.strip().strip('·▸•').strip()
            if line and len(line) < 80:
                profile.target_roles.append(line)

    # Summary
    summary_match = re.search(r'PROFESSIONAL SUMMARY(.*?)(?:\nEXPERIENCE)', resume_text, re.DOTALL)
    if summary_match:
        profile.summary = summary_match.group(1).strip()[:500]

    return profile
