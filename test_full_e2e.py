#!/usr/bin/env python3
"""
CareerPilot AI — Full End-to-End Test: Register → Profile → Scrape → Match → Cover Letter → Apply
Uses urllib (no external deps). Targets localhost:7899.
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:7899/api"
SUFFIX = sys.argv[1] if len(sys.argv) > 1 else str(int(time.time()))
EMAIL = f"e2e_test_{SUFFIX}@careerpilot.ai"
PASSWORD = "TestPass123!"
NAME = f"E2E Test User {SUFFIX}"

pass_count = 0
fail_count = 0


def api(method, path, data=None, token=None, timeout=60):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return {
                "status": resp.status,
                "data": json.loads(raw) if raw and resp.status != 204 else None,
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode()[:500]}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def check(name, condition, detail=""):
    global pass_count, fail_count
    if condition:
        pass_count += 1
        print(f"  ✓ PASS: {name} {detail}")
    else:
        fail_count += 1
        print(f"  ✗ FAIL: {name} {detail}")
    return condition


def section(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


# ── 1. Health Check ──────────────────────────────────────────
section("1. HEALTH CHECK")
r = api("GET", "/health")
check("Backend health", r["status"] == 200 and r["data"] and r["data"].get("status") == "ok",
      f"→ {json.dumps(r.get('data',{}))}")

# ── 2. Register New User ─────────────────────────────────────
section("2. REGISTER NEW USER")
r = api("POST", "/auth/register", {
    "email": EMAIL,
    "password": PASSWORD,
    "name": NAME,
})
ok = r["status"] in (200, 201)
user_data = r.get("data", {}) if ok else {}
token = user_data.get("access_token", "")
user_id = user_data.get("user_id", "")
check("Registration", ok and bool(token), f"email={EMAIL}")
if not token:
    print("  Cannot continue without token — aborting.")
    sys.exit(1)
print(f"  user_id={user_id}")
print(f"  token={token[:40]}...")

# ── 3. Login Verification ────────────────────────────────────
section("3. LOGIN VERIFICATION")
r = api("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})
ok = r["status"] in (200, 201) and "access_token" in r.get("data", {})
check("Login with same credentials", ok)
if ok:
    token = r["data"]["access_token"]  # use fresh token

# ── 4. Update User Profile ───────────────────────────────────
section("4. UPDATE USER PROFILE")
profile_data = {
    "preferred_roles": ["Network Engineer", "SOC Analyst"],
    "preferred_location": "Bangalore",
    "skills": ["Cisco", "Firewall", "IDS/IPS", "SIEM", "Linux", "Python", "Wireshark", "TCP/IP"],
}
r = api("PUT", "/user-profile/", profile_data, token=token)
check("Profile update", r["status"] == 200, f"→ roles={profile_data['preferred_roles']}")

# ── 5. Verify Profile ────────────────────────────────────────
section("5. VERIFY PROFILE (GET)")
r = api("GET", "/user-profile/", token=token)
ok = r["status"] == 200
profile = r.get("data", {}) if ok else {}
check("GET profile", ok)
if ok:
    check("Preferred location set", profile.get("preferred_location") == "Bangalore",
          f"→ {profile.get('preferred_location')}")
    check("Preferred roles set", len(profile.get("preferred_roles", [])) > 0,
          f"→ {profile.get('preferred_roles')}")

# ── 6. Initial Jobs (should be 0 for new user) ───────────────
section("6. INITIAL JOBS (isolation check)")
r = api("GET", "/jobs/", token=token)
ok = r["status"] == 200
initial_total = r.get("data", {}).get("total", -1) if ok else -1
check("GET /jobs/ succeeds", ok)
check("New user sees 0 jobs initially", initial_total == 0,
      f"(got {initial_total})")

# ── 7. Trigger Job Scrape ────────────────────────────────────
section("7. TRIGGER JOB SCRAPE")
r = api("POST", "/scraper/trigger", {"location": "Bangalore"}, token=token)
task_id = r.get("data", {}).get("task_id", "") if r["status"] == 200 else ""
check("Scrape triggered", r["status"] == 200 and bool(task_id),
      f"task_id={task_id[:30]}...")

# ── 8. Wait for Scrape ───────────────────────────────────────
section("8. WAIT FOR SCRAPE (polling)")
scrape_done = False
for i in range(40):
    time.sleep(10)
    r = api("GET", "/dashboard/stats", token=token)
    if r["status"] == 200:
        scraper = r["data"].get("scraper", {})
        total = scraper.get("total_jobs", 0)
        scraping = scraper.get("is_scraping", True)
        last = scraper.get("last_scrape_at", "?")
        print(f"  Poll {i+1:2d}: total_jobs={total:4d}  is_scraping={scraping}  last={last[:25]}")
        if not scraping and total > 0:
            scrape_done = True
            break
    else:
        print(f"  Poll {i+1:2d}: status error {r.get('status')}")
else:
    print("  ⚠ Scrape may still be running; continuing...")
check("Scrape completed with jobs", scrape_done, "(or continuing)")

# ── 9. Check Jobs After Scrape ───────────────────────────────
section("9. JOBS AFTER SCRAPE")
r = api("GET", "/jobs/", token=token)
ok = r["status"] == 200
final_total = r.get("data", {}).get("total", -1) if ok else -1
check("GET /jobs/ after scrape", ok)
check("Jobs > 0 after scrape", final_total > 0, f"total={final_total}")
# Show sample
jobs_list = r.get("data", {}).get("data", []) if ok else []
if jobs_list:
    print(f"  Sample jobs:")
    for j in jobs_list[:3]:
        print(f"    [{j.get('source','?'):8s}] {j.get('title','?')[:60]} @ {j.get('company','?')[:25]}")

# ── 10. Trigger Scoring ──────────────────────────────────────
section("10. TRIGGER JOB SCORING")
r = api("POST", "/scraper/score-jobs", {}, token=token)
check("Scoring triggered", r["status"] == 200,
      f"→ {json.dumps(r.get('data',{}))[:120]}")

# ── 11. Wait for Scoring ─────────────────────────────────────
section("11. WAIT FOR SCORING")
scoring_done = False
for i in range(15):
    time.sleep(4)
    r = api("GET", "/scraper/status", token=token)
    if r["status"] == 200:
        matched = r["data"].get("matched_jobs", -1)
        print(f"  Poll {i+1:2d}: matched_jobs={matched}")
        if matched > 0:
            scoring_done = True
            break
    else:
        print(f"  Poll {i+1:2d}: status error {r.get('status')}")
check("Scoring completed with matches", scoring_done, "(or continuing)")

# ── 12. Get Matched Jobs ─────────────────────────────────────
section("12. GET MATCHED JOBS")
r = api("GET", "/jobs/matches?min_score=10&limit=10", token=token)
ok = r["status"] == 200
matches = r.get("data", []) if ok else []
# data may be wrapped
if isinstance(r.get("data"), dict):
    matches = r["data"].get("matches", r["data"].get("data", []))
count = len(matches)
check("GET /jobs/matches succeeds", ok)
check("Matches returned", count > 0, f"{count} matches")

top_job = None
for m in matches[:5]:
    score = m.get("score", m.get("relevance_score", m.get("match_score", "?")))
    tier = m.get("tier", "?")
    title = m.get("title", "?")[:55]
    company = m.get("company", "?")[:20]
    loc = m.get("location", "?")[:25]
    print(f"  {str(score):>5s} | {tier:10s} | {title} @ {company} ({loc})")
    if not top_job:
        top_job = m

# ── 13. Generate Cover Letter ────────────────────────────────
section("13. GENERATE COVER LETTER")
if top_job and "id" in top_job:
    job_id = top_job["id"]
    r = api("POST", f"/jobs/{job_id}/generate-cover-letter", {}, token=token)
    ok_cover = r["status"] == 200 or r["status"] == 201
    letter_data = r.get("data", {}) if ok_cover else {}
    letter_content = letter_data.get("content", letter_data.get("cover_letter", ""))
    check("Cover letter generated", ok_cover and len(letter_content) > 100,
          f"{len(letter_content)} chars")
    if letter_content:
        print(f"  Preview: {letter_content[:200]}...")
    cover_letter_id = letter_data.get("id", "")
else:
    cover_letter_id = ""
    check("Cover letter — skipped (no top job)", True)

# ── 14. Submit Application ───────────────────────────────────
section("14. SUBMIT APPLICATION")
if top_job and "id" in top_job:
    job_id = top_job["id"]
    apply_data = {
        "job_posting_id": job_id,
        "method": "manual",
    }
    if cover_letter_id:
        apply_data["cover_letter_id"] = cover_letter_id

    # Apply via job apply endpoint
    r = api("POST", f"/jobs/{job_id}/apply", token=token)
    ok_apply = r["status"] == 200 and r.get("data", {}).get("status") == "applied"
    check("Application submitted", ok_apply,
          f"→ {json.dumps(r.get('data',{}))[:200]}")
    app_data = r.get("data", {}) if ok_apply else {}
    app_id = app_data.get("application_id", "")
else:
    check("Application — skipped (no top job)", True)

# ── 15. Verify Application Exists ────────────────────────────
section("15. VERIFY APPLICATION IN LIST")
r = api("GET", "/applications/", token=token)
ok = r["status"] == 200
apps = r.get("data", []) if ok else []
if isinstance(r.get("data"), dict):
    apps = r.get("data").get("data", r.get("data").get("applications", []))
check("GET /applications/ succeeds", ok)
check("Application list returns data", len(apps) > 0, f"{len(apps)} apps")
for a in apps[:3]:
    print(f"  app_id={a.get('id','?')[:12]}... status={a.get('status','?')} method={a.get('method','?')}")

# ── 16. Dashboard Stats ──────────────────────────────────────
section("16. DASHBOARD STATS")
r = api("GET", "/dashboard/stats", token=token)
ok = r["status"] == 200
stats = r.get("data", {}) if ok else {}
check("Dashboard stats", ok)
if ok:
    scraper = stats.get("scraper", {})
    print(f"  scraper: total_jobs={scraper.get('total_jobs','?')} "
          f"is_scraping={scraper.get('is_scraping','?')} "
          f"last_scrape={str(scraper.get('last_scrape_at','?'))[:25]}")
    src_breakdown = scraper.get("source_breakdown", {})
    if src_breakdown:
        print(f"  sources: {json.dumps(src_breakdown)}")

# ── 17. Verify user_jobs table ───────────────────────────────
section("17. VERIFY user_jobs TABLE")
import subprocess
r2 = subprocess.run(
    ["docker", "exec", "-i", "careerpilot-postgres", "psql", "-U", "careerpilot",
     "-d", "careerpilot", "-tAc",
     f"SELECT COUNT(*) FROM user_jobs WHERE user_id = '{user_id}'"],
    capture_output=True, text=True, timeout=15
)
if r2.returncode == 0 and r2.stdout.strip().isdigit():
    mapped_count = int(r2.stdout.strip())
    check("user_jobs table populated", mapped_count > 0,
          f"{mapped_count} rows for this user")
else:
    check("user_jobs table populated", False, f"query error: {r2.stderr[:100]}")

# ── Summary ──────────────────────────────────────────────────
section("FINAL SUMMARY")
print(f"  Passed: {pass_count}")
print(f"  Failed: {fail_count}")
print(f"  User:  {user_id}")
print(f"  Email: {EMAIL}")
print(f"  Jobs:  {final_total}")
print(f"  Matches: {count}")

if fail_count == 0:
    print("\n  ✓ ALL TESTS PASSED — Register → Profile → Scrape → Match → Cover Letter → Apply")
else:
    print(f"\n  ✗ {fail_count} TEST(S) FAILED")

sys.exit(0 if fail_count == 0 else 1)