"""
Shared in-memory state for CareerPilot AI.
This module holds the global in-memory stores that are shared across routers.
"""

# Resume store
_resumes: list[dict] = []

# Job store
_jobs: list[dict] = []

# Match store
_matches: list[dict] = []

# Application store
_applications: list[dict] = []

# Approval store
_approvals: list[dict] = []

# Activity feed store (for dashboard)
_activities: list[dict] = []


def get_resumes() -> list[dict]:
    return _resumes


def add_resume(resume: dict) -> None:
    _resumes.append(resume)


def remove_resume(resume_id: str, user_id: str) -> bool:
    """Remove a resume if it belongs to the user. Returns True if removed."""
    global _resumes
    for i, r in enumerate(_resumes):
        if r["id"] == resume_id and r["user_id"] == user_id:
            _resumes.pop(i)
            return True
    return False


def get_jobs() -> list[dict]:
    return _jobs


def add_job(job: dict) -> None:
    _jobs.append(job)


def get_matches() -> list[dict]:
    return _matches


def add_match(match: dict) -> None:
    _matches.append(match)


def get_applications() -> list[dict]:
    return _applications


def add_application(application: dict) -> None:
    _applications.append(application)


def get_approvals() -> list[dict]:
    return _approvals


def add_approval(approval: dict) -> None:
    _approvals.append(approval)


def get_activities() -> list[dict]:
    return _activities


def add_activity(activity: dict) -> None:
    _activities.append(activity)
    # Keep only last 50 activities
    if len(_activities) > 50:
        _activities[:] = _activities[-50:]


def clear_activities() -> None:
    _activities.clear()


# Helper functions to get counts
def get_resume_count() -> int:
    return len(_resumes)


def get_job_count() -> int:
    return len(_jobs)


def get_match_count() -> int:
    return len(_matches)


def get_application_count() -> int:
    return len(_applications)


def get_approval_count() -> int:
    return len(_approvals)


def get_activity_count() -> int:
    return len(_activities)