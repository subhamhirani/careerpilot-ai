-- ============================================================
-- Migration: Fix job_postings schema + migrate careerpilot_jobs
-- ============================================================

-- 1. Add missing hash_key column for dedup
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS hash_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ix_job_postings_hash_key ON job_postings(hash_key) WHERE hash_key IS NOT NULL;

-- 2. Change company_id to be nullable (some jobs may not have a known company)
ALTER TABLE job_postings ALTER COLUMN company_id DROP NOT NULL;

-- 3. Add missing columns referenced by the scraper
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'new';

-- ============================================================
-- Migrate existing data from careerpilot_jobs → job_postings
-- ============================================================

-- 3a. Insert unique companies from careerpilot_jobs
INSERT INTO companies (id, name)
SELECT gen_random_uuid(), TRIM(company)
FROM (
    SELECT DISTINCT TRIM(company) AS company
    FROM careerpilot_jobs
    WHERE TRIM(company) != ''
) AS c
WHERE NOT EXISTS (
    SELECT 1 FROM companies WHERE name = c.company
);

-- 3b. Insert jobs from careerpilot_jobs into job_postings
--     (use source_url as hash_key)
INSERT INTO job_postings (
    id,
    company_id,
    title,
    description,
    location,
    source_url,
    source_platform,
    external_id,
    posted_at,
    hash_key,
    status,
    is_active,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid() AS id,
    (SELECT co.id FROM companies co WHERE co.name = TRIM(cj.company) LIMIT 1) AS company_id,
    cj.title,
    cj.description,
    cj.location,
    cj.url,
    cj.source,
    cj.source_job_id,
    NULLIF(cj.posted_at, '')::timestamptz,
    cj.hash_key,
    'new' AS status,
    true AS is_active,
    cj.created_at,
    cj.created_at AS updated_at
FROM careerpilot_jobs cj
WHERE NOT EXISTS (
    SELECT 1 FROM job_postings jp WHERE jp.hash_key = cj.hash_key
);

-- 3c. Link all jobs to the existing user
INSERT INTO user_jobs (user_id, job_posting_id, status)
SELECT
    up.user_id,
    jp.id,
    'new'
FROM job_postings jp
CROSS JOIN (SELECT DISTINCT user_id FROM user_profiles) up
WHERE NOT EXISTS (
    SELECT 1 FROM user_jobs uj
    WHERE uj.job_posting_id = jp.id AND uj.user_id = up.user_id
)
ON CONFLICT (user_id, job_posting_id) DO NOTHING;
