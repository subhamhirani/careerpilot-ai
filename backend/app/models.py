"""
CareerPilot AI — SQLAlchemy ORM Models.

All tables use UUID primary keys, JSONB for flexible fields,
and VECTOR(384) for embedding columns (pgvector).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

# ──────────────────────────────────────────────
#  Declarative base
# ──────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
#  Utility helpers
# ──────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# Register a custom type for pgvector so Alembic can see it.
# We define a simple wrapper; in production use pgvector's built-in SQLAlchemy type.
try:
    from pgvector.sqlalchemy import Vector as _PGVector

    Vector384 = _PGVector(384)
except ImportError:
    # Fallback when pgvector is not installed (CI / dev)
    from sqlalchemy import LargeBinary

    Vector384 = LargeBinary(384 * 4)  # 384 floats × 4 bytes


# ──────────────────────────────────────────────
#  Enums (stored as strings in DB)
# ──────────────────────────────────────────────

class UserRole(str, PyEnum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class ApplicationStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApprovalStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MatchGrade(str, PyEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class AuditAction(str, PyEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    APPROVE = "approve"
    REJECT = "reject"
    GENERATE = "generate"
    SUBMIT = "submit"


# ──────────────────────────────────────────────
#  User & Authentication
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_constraint=True),
        default=UserRole.CANDIDATE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.false(), default=False, nullable=False
    )
    totp_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.false(), default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    profiles: Mapped[List["UserProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[List["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[List["CoverLetter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pending_approvals: Mapped[List["PendingApproval"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    telegram_settings: Mapped[Optional["TelegramSettings"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    search_preferences: Mapped[List["SearchPreference"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"


# ──────────────────────────────────────────────
#  Company
# ──────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    job_postings: Mapped[List["JobPosting"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company {self.name}>"


# ──────────────────────────────────────────────
#  Resume & Versions
# ──────────────────────────────────────────────

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # pdf, docx, etc.
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector384, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="resumes")
    versions: Mapped[List["ResumeVersion"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resume {self.title} user={self.user_id}>"


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector384, nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    resume: Mapped["Resume"] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<ResumeVersion {self.version_number} resume={self.resume_id}>"


# ──────────────────────────────────────────────
#  User Profile
# ──────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    headline: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    experience: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    education: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    certifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    preferred_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preferred_roles: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector384, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profiles")

    def __repr__(self) -> str:
        return f"<UserProfile {self.full_name}>"


# ──────────────────────────────────────────────
#  Job Posting
# ──────────────────────────────────────────────

class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # onsite, hybrid, remote
    employment_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # full-time, part-time, contract
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True, default="USD")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    responsibilities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    skills_required: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector384, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_platform: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # linkedin, indeed, etc.
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="job_postings")
    match_scores: Mapped[List["MatchScore"]] = relationship(
        back_populates="job_posting", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        back_populates="job_posting", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JobPosting {self.title} @ {self.company_id}>"


# ──────────────────────────────────────────────
#  Match Score (resume ↔ job)
# ──────────────────────────────────────────────

class MatchScore(Base):
    __tablename__ = "match_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skills_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    education_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    grade: Mapped[Optional[MatchGrade]] = mapped_column(
        Enum(MatchGrade, name="match_grade", create_constraint=True), nullable=True
    )
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship()
    job_posting: Mapped["JobPosting"] = relationship(back_populates="match_scores")
    resume: Mapped["Resume"] = relationship()

    def __repr__(self) -> str:
        return f"<MatchScore {self.overall_score} job={self.job_posting_id}>"


# ──────────────────────────────────────────────
#  Cover Letter
# ──────────────────────────────────────────────

class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="professional")
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_approved: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.false(), default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="cover_letters")
    job_posting: Mapped["JobPosting"] = relationship()

    def __repr__(self) -> str:
        return f"<CoverLetter {self.title}>"


# ──────────────────────────────────────────────
#  Pending Approval (human-in-the-loop)
# ──────────────────────────────────────────────

class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # cover_letter, application, resume
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status", create_constraint=True),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )
    requested_action: Mapped[str] = mapped_column(String(64), nullable=False)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="pending_approvals")

    def __repr__(self) -> str:
        return f"<PendingApproval {self.entity_type}/{self.entity_id} → {self.status}>"


# ──────────────────────────────────────────────
#  Application
# ──────────────────────────────────────────────

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", create_constraint=True),
        default=ApplicationStatus.DRAFT,
        nullable=False,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="applications")
    job_posting: Mapped["JobPosting"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship()
    cover_letter: Mapped["CoverLetter"] = relationship()

    def __repr__(self) -> str:
        return f"<Application {self.status} job={self.job_posting_id}>"


# ──────────────────────────────────────────────
#  Audit Log
# ──────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", create_constraint=True), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type}/{self.entity_id}>"


# ──────────────────────────────────────────────
#  Telegram Settings
# ──────────────────────────────────────────────

class TelegramSettings(Base):
    __tablename__ = "telegram_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    chat_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    digest_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    discovery_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="telegram_settings")

    def __repr__(self) -> str:
        return f"<TelegramSettings user={self.user_id} chat={self.chat_id}>"


# ──────────────────────────────────────────────
#  Search Preference
# ──────────────────────────────────────────────

class SearchPreference(Base):
    __tablename__ = "search_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Default Search")
    keywords: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    locations: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    remote_types: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    employment_types: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    industries: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    notify_on_match: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.true(), default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="search_preferences")

    def __repr__(self) -> str:
        return f"<SearchPreference {self.name}>"
