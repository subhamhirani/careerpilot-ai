"""CareerPilot AI - Initial database schema with all 14 tables

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-06-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("totp_secret", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- companies ---
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
    )

    # --- resumes ---
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("is_original", sa.Boolean(), server_default=sa.text("TRUE")),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- resume_versions ---
    op.create_table(
        "resume_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("version_type", sa.String(), nullable=False),
        sa.Column("file_path_pdf", sa.String(), nullable=True),
        sa.Column("file_path_docx", sa.String(), nullable=True),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- user_profiles ---
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- job_postings ---
    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("hash_key", sa.String(), unique=True, nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("status", sa.String(), server_default=sa.text("'new'")),
        sa.Column("embedding", sa.Text(), nullable=True),  # JSON-serialized vector
    )

    # Create pgvector-style index for job_postings embedding
    op.execute(
        "CREATE INDEX idx_job_postings_embedding ON job_postings "
        "USING ivfflat (CAST(embedding AS vector(384)) vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # --- match_scores ---
    op.create_table(
        "match_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("reasons_json", postgresql.JSONB(), nullable=True),
        sa.Column("missing_skills_json", postgresql.JSONB(), nullable=True),
        sa.Column("risk_indicators_json", postgresql.JSONB(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- cover_letters ---
    op.create_table(
        "cover_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(), server_default=sa.text("'formal'")),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- pending_approvals ---
    op.create_table(
        "pending_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id"), nullable=False),
        sa.Column("resume_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resume_versions.id"), nullable=True),
        sa.Column("cover_letter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cover_letters.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), server_default=sa.text("'pending'")),
    )

    # --- applications ---
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id"), nullable=False),
        sa.Column("resume_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resume_versions.id"), nullable=True),
        sa.Column("cover_letter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cover_letters.id"), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("method", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default=sa.text("'submitted'")),
        sa.Column("confirmation_id", sa.String(), nullable=True),
        sa.Column("screenshot_before", sa.String(), nullable=True),
        sa.Column("screenshot_after", sa.String(), nullable=True),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- telegram_settings ---
    op.create_table(
        "telegram_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bot_token", sa.String(), nullable=False),
        sa.Column("chat_id", sa.String(), nullable=False),
        sa.Column("allowed_user_id", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("TRUE")),
        sa.Column("notify_excellent_only", sa.Boolean(), server_default=sa.text("FALSE")),
    )

    # --- search_preferences ---
    op.create_table(
        "search_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("locations_json", postgresql.JSONB(), server_default=sa.text("'[\"Ahmedabad\",\"Gandhinagar\",\"GIFT City\",\"Remote\",\"India\",\"International\"]'")),
        sa.Column("roles_json", postgresql.JSONB(), nullable=True),
        sa.Column("exclude_keywords_json", postgresql.JSONB(), server_default=sa.text("'[\"Linux Administrator only\",\"Cybersecurity only\",\"Full Stack Developer\"]'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Indexes ---
    op.create_index("idx_match_scores_score_desc", "match_scores", ["score"], postgresql_using="btree")
    op.create_index("idx_match_scores_tier", "match_scores", ["tier"])
    op.create_index("idx_match_scores_user", "match_scores", ["user_id"])
    op.create_index("idx_job_postings_status", "job_postings", ["status", "discovered_at"])
    op.create_index("idx_job_postings_source", "job_postings", ["source"])
    op.create_index("idx_resumes_user", "resumes", ["user_id"])
    op.create_index("idx_applications_user", "applications", ["user_id"])
    op.create_index("idx_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("idx_audit_logs_agent", "audit_logs", ["agent_name"])


def downgrade() -> None:
    op.drop_table("search_preferences")
    op.drop_table("telegram_settings")
    op.drop_table("audit_logs")
    op.drop_table("applications")
    op.drop_table("pending_approvals")
    op.drop_table("cover_letters")
    op.drop_table("match_scores")
    op.drop_table("job_postings")
    op.drop_table("user_profiles")
    op.drop_table("resume_versions")
    op.drop_table("resumes")
    op.drop_table("companies")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
