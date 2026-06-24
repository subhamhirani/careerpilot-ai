-- CareerPilot AI — Per-User Job Isolation
-- Adds user_jobs mapping table and migration data

-- Step 1: Create user_jobs mapping table
CREATE TABLE IF NOT EXISTS user_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_posting_id UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'new',  -- new, saved, rejected, applied
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_posting_id)
);

-- Step 2: Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_jobs_user_id ON user_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_jobs_job_id ON user_jobs(job_posting_id);
CREATE INDEX IF NOT EXISTS idx_user_jobs_status ON user_jobs(user_id, status);

-- Step 3: Migrate data — assign existing global jobs to a "system" default
-- (keeps backward compatibility for existing jobs)
DO $$
BEGIN
    -- Only migrate if user_jobs is empty and we have job_postings
    IF EXISTS (SELECT 1 FROM job_postings LIMIT 1) AND NOT EXISTS (SELECT 1 FROM user_jobs LIMIT 1) THEN
        -- Insert mapping for all jobs to a placeholder system user (first user)
        INSERT INTO user_jobs (user_id, job_posting_id, status)
        SELECT u.id, jp.id, jp.status
        FROM job_postings jp
        CROSS JOIN (SELECT id FROM users ORDER BY created_at LIMIT 1) u
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
