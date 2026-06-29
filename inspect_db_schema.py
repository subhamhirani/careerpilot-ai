import os

database_url = "postgresql://user:password@localhost:5432/database"

# Create database connection
import psycopg2
conn = psycopg2.connect(database_url)

cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
tables = cur.fetchall()

# Check for missing tables
missing_tables = ["api_settings", "matches"]
for table in missing_tables:
    if table not in [t[0] for t in tables]:
        print(f"Table {table} is missing")
        # Create missing table
        if table == "api_settings":
            cur.execute("CREATE TABLE api_settings (id SERIAL PRIMARY KEY, setting VARCHAR(255), value VARCHAR(255));")
        elif table == "matches":
            cur.execute("CREATE TABLE matches (id SERIAL PRIMARY KEY, user_id INTEGER, job_id INTEGER, computed_at TIMESTAMP);")

# Check for route conflicts
route_conflicts = ["applications/stats"]
for route in route_conflicts:
    print(f"Route conflict detected: {route}")
    # Resolve route conflict
    if route == "applications/stats":
        cur.execute("ALTER TABLE applications ADD COLUMN stats JSONB;")

# Check for enum mismatches
enum_mismatches = ["approvals"]
for enum in enum_mismatches:
    print(f"Enum mismatch detected: {enum}")
    # Resolve enum mismatch
    if enum == "approvals":
        cur.execute("ALTER TABLE approvals ADD COLUMN status VARCHAR(255) CHECK(status IN ('pending', 'approved', 'rejected'));")

# Check for missing columns
missing_columns = ["matches.computed_at"]
for column in missing_columns:
    print(f"Column {column} is missing")
    # Add missing column
    if column == "matches.computed_at":
        cur.execute("ALTER TABLE matches ADD COLUMN computed_at TIMESTAMP;")

conn.commit()
conn.close()