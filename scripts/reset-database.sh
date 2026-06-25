#!/bin/bash
set -e

echo "🗑️  CareerPilot Database Reset Script"
echo "======================================"
echo ""
echo "⚠️  This will DELETE ALL DATA including:"
echo "   - All users and profiles"
echo "   - All job postings"
echo "   - All applications"
echo "   - All cover letters"
echo "   - All match scores"
echo "   - All settings"
echo ""
echo "✅  What will be preserved:"
echo "   - Database schema (tables, indexes)"
echo "   - Alembic migration history"
echo ""

read -p "Are you sure you want to continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "❌ Aborted - no changes made"
  exit 1
fi

echo ""
echo "📡 Dropping all tables..."

docker compose exec -T postgres psql -U careerpilot -d careerpilot <<EOF
-- Disable foreign key checks temporarily
SET CONSTRAINTS ALL DEFERRED;

-- Drop all tables in correct order (dependencies first)
DROP TABLE IF EXISTS telegram_settings CASCADE;
DROP TABLE IF EXISTS pending_approvals CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS cover_letters CASCADE;
DROP TABLE IF EXISTS match_scores CASCADE;
DROP TABLE IF EXISTS user_jobs CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS job_postings CASCADE;
DROP TABLE IF EXISTS careerpilot_jobs CASCADE;
DROP TABLE IF EXISTS search_preferences CASCADE;
DROP TABLE IF EXISTS resume_versions CASCADE;
DROP TABLE IF EXISTS resumes CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS process_statuses CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;

-- Reset sequences
DROP SEQUENCE IF EXISTS users_id_seq CASCADE;
DROP SEQUENCE IF EXISTS job_postings_id_seq CASCADE;
DROP SEQUENCE IF EXISTS companies_id_seq CASCADE;

-- Recreate alembic_version table
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL
);

-- Re-insert initial migration
INSERT INTO alembic_version (version_num) VALUES ('001');

EOF

echo ""
echo "✅ Database reset complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Run migrations: docker compose exec backend alembic upgrade head"
echo "   2. Restart backend: docker compose restart backend worker"
echo "   3. Create first user via /register endpoint"
echo ""
echo "🎉 Fresh database ready!"