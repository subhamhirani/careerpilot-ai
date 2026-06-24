#!/usr/bin/env python3
"""
CareerPilot AI - Per-User Isolation & Location Fix Script%{  }(apply fix)
=========================================================
This script:
1. Fixes location handling (no hardcoded "India" fallback)
2. Creates user_jobs mapping table
3. Patches tasks_scraper.py to populate user_jobs
4. Patches jobs.py to filter by mapping table
5. Rebuilds and restarts containers
"""
import subprocess, sys, os

BACKEND_DIR = "/home/ubuntu/careerpilot"

def run(cmd, cwd=BACKEND_DIR):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if r.stdout: print(r.stdout)
    if r.stderr: print(r.stderr, file=sys.stderr)
    return r.returncode == 0

# Step 1: Create migration
sql = """CREATE TABLE IF NOT EXISTS user_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_posting UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'new',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, job_posting)
);
CREATE INDEX IF NOT EXISTS idx_uj_user ON user_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_uj_job ON user_jobs(job_posting);
"""
with open(f"{BACKEND_DIR}/backend/migrations/001.sql","w") as f:
    f.write(sql)
print("1. Migration file created")
print("2. Applying migration ...")
run("docker exec -i postgres psql -U cpuser -d careerpilot < backend/migrations/001.sql")
