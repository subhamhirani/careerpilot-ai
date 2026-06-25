-- CareerPilot AI - Initialize database schema
-- Run this when alembic migrations are unavailable

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables in dependency order

-- users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    totp_secret VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- companies
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    website VARCHAR,
    industry VARCHAR
);

-- resumes
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    is_original BOOLEAN DEFAULT TRUE,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- resume_versions
CREATE TABLE IF NOT EXISTS resume_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id),
    version_type VARCHAR NOT NULL,
    file_path_pdf VARCHAR,
    file_path_docx VARCHAR,
    job_posting_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- user_profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    raw_json JSONB NOT NULL,
    embedding BYTEA,
    parsed_at TIMESTAMPTZ DEFAULT NOW()
);

-- job_postings
CREATE TABLE IF NOT EXISTS job_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    title VARCHAR NOT NULL,
    description TEXT,
    location VARCHAR,
    url VARCHAR NOT NULL,
    source VARCHAR,
    salary_min INTEGER,
    salary_max INTEGER,
    posted_at TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    hash_key VARCHAR UNIQUE,
    is_duplicate BOOLEAN DEFAULT FALSE,
    status VARCHAR DEFAULT 'new',
    embedding TEXT
);

-- Create pgvector index for job_postings embedding
CREATE INDEX IF NOT EXISTS idx_job_postings_embedding ON job_postings 
USING ivfflat (CAST(embedding AS vector(384)) vector_cosine_ops) 
WITH (lists = 100);

-- match_scores
CREATE TABLE IF NOT EXISTS match_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_posting_id UUID NOT NULL REFERENCES job_postings(id),
    user_id UUID NOT NULL REFERENCES users(id),
    score INTEGER NOT NULL,
    tier VARCHAR NOT NULL,
    reasons_json JSONB,
    missing_skills_json JSONB,
    risk_indicators_json JSONB,
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- cover_letters
CREATE TABLE IF NOT EXISTS cover_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_posting_id UUID NOT NULL REFERENCES job_postings(id),
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    tone VARCHAR DEFAULT 'formal',
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- pending_approvals
CREATE TABLE IF NOT EXISTS pending_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    job_posting_id UUID NOT NULL REFERENCES job_postings(id),
    resume_version_id UUID REFERENCES resume_versions(id),
    cover_letter_id UUID REFERENCES cover_letters(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    status VARCHAR DEFAULT 'pending'
);

-- applications
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    job_posting_id UUID NOT NULL REFERENCES job_postings(id),
    resume_version_id UUID REFERENCES resume_versions(id),
    cover_letter_id UUID REFERENCES cover_letters(id),
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    method VARCHAR,
    status VARCHAR DEFAULT 'submitted',
    confirmation_id VARCHAR,
    screenshot_before VARCHAR,
    screenshot_after VARCHAR
);

-- audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    entity_type VARCHAR,
    entity_id UUID,
    result VARCHAR,
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- telegram_settings
CREATE TABLE IF NOT EXISTS telegram_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    bot_token VARCHAR NOT NULL,
    chat_id VARCHAR NOT NULL,
    allowed_user_id VARCHAR NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    notify_excellent_only BOOLEAN DEFAULT FALSE
);

-- search_preferences
CREATE TABLE IF NOT EXISTS search_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    locations_json JSONB DEFAULT '["Ahmedabad","Gandhinagar","GIFT City","Remote","India","International"]',
    roles_json JSONB,
    exclude_keywords_json JSONB DEFAULT '["Linux Administrator only","Cybersecurity only","Full Stack Developer"]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- process_statuses (from migration 97dde6c91118)
CREATE TABLE IF NOT EXISTS process_statuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    progress_pct INTEGER NOT NULL DEFAULT 0,
    current_step VARCHAR,
    total_steps INTEGER,
    metadata_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_match_scores_score_desc ON match_scores (score DESC);
CREATE INDEX IF NOT EXISTS idx_match_scores_tier ON match_scores (tier);
CREATE INDEX IF NOT EXISTS idx_match_scores_user ON match_scores (user_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_status ON job_postings (status, discovered_at);
CREATE INDEX IF NOT EXISTS idx_job_postings_source ON job_postings (source);
CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes (user_id);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_agent ON audit_logs (agent_name);

-- Update alembic version to latest
UPDATE alembic_version SET version_num = '97dde6c91118';