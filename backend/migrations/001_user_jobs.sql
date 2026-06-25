-- CareerPilot AI: Create user_jobs mapping table for per-user job isolation
CREATE TABLE IF NOT EXISTS user_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_posting_id UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_posting_id)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_jobs_user ON user_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_jobs_job ON user_jobs(job_posting_id);