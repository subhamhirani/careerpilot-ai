#!/usr/bin/env python3
"""Full integration test for CareerPilot scraper system."""
import json, os, sys, time, urllib.request, urllib.error

BASE = "http://localhost:7899"

def api(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        return {"error": e.code, "body": body}

# 1. Login (user may already exist)
# Demo credentials — replace with your own for production
print("=== 1. LOGIN ===")
r = api("POST", "/api/auth/login", {"email": "demo@careerpilot.ai", "password": "DemoPass123!"})
token = r.get("access_token", "")
if not token:
    print("  Login failed, registering...")
    r = api("POST", "/api/auth/register", {"email": "demo@careerpilot.ai", "password": "DemoPass123!"})
    token = r.get("access_token", "")
    if token:
        print(f"  Registered + logged in")
    else:
        print(f"  Register error: {r.get('error')} - {r.get('body')}")
        sys.exit(1)
else:
    print(f"  Logged in OK")

print(f"  Token: {token[:30]}...")

# 2. Upload resume to create a user profile
print("\n=== 2. UPLOAD RESUME ===")
resume_path = "/home/ubuntu/careerpilot/storage/resumes/example_resume.txt"
if not os.path.exists(resume_path):
    # Create an example resume if none exists
    os.makedirs(os.path.dirname(resume_path), exist_ok=True)
    with open(resume_path, "w") as f:
        f.write("""John Doe
Software Engineer with 3+ years of experience in Python, Docker, and cloud infrastructure.
Skills: Python, Docker, Kubernetes, AWS, Linux, Git, CI/CD, PostgreSQL
Experience:
- Senior Software Engineer at TechCorp (2 years)
- Junior Developer at StartupInc (1 year)
Education: B.Tech in Computer Science
Target Roles: DevOps Engineer, Cloud Engineer, SRE
Preferred Location: Remote, India""")

with open(resume_path, "r") as f:
    resume_text = f.read()

r = api("POST", "/api/resumes/upload", {"resume_text": resume_text}, token=token)
print(f"  Resume upload: {json.dumps(r, indent=2)[:200]}")

# 3. Scraper status
print("\n=== 3. SCRAPER STATUS ===")
r = api("GET", "/api/scraper/status", token=token)
print(json.dumps(r, indent=2))

# 4. Trigger scrape
print("\n=== 4. TRIGGER SCRAPE ===")
# Clear old jobs first? No, let Celery do its thing.
r = api("POST", "/api/scraper/trigger", {}, token=token)
print(f"  Task: {r.get('task_id','?')[:20]}... Status: {r.get('status')}")

# 5. Wait for scrape
print("\n=== 5. WAITING FOR SCRAPE ===")
for i in range(30):
    time.sleep(5)
    r = api("GET", "/api/scraper/status", token=token)
    total = r.get("total_jobs", 0)
    linkedin = r.get("linkedin_jobs", 0)
    naukri = r.get("naukri_jobs", 0)
    print(f"  Poll {i+1}: total={total} li={linkedin} nauk={naukri}")
    if total > 50:
        print("  Good data!")
        break

# 6. Run scoring
print("\n=== 6. TRIGGER SCORING ===")
r = api("POST", "/api/scraper/score-jobs", {}, token=token)
print(f"  Scoring: {json.dumps(r, indent=2)[:200]}")

# 7. Wait for scoring
print("\n=== 7. WAITING FOR SCORING ===")
for i in range(15):
    time.sleep(3)
    r = api("GET", "/api/scraper/status", token=token)
    matched = r.get("matched_jobs", 0)
    print(f"  Poll {i+1}: {matched} matched jobs")
    if matched > 5:
        break

# 8. Get matches
print("\n=== 8. TOP MATCHES ===")
r = api("GET", "/api/jobs/matches?min_score=10&limit=10", token=token)
matches = r.get("matches", [])
print(f"Total matches: {r.get('count', 0)}")
for m in matches[:10]:
    matched_skills = m.get("matched_skills", [])
    missing = m.get("missing_skills", [])
    print(f"  {m['relevance_score']:5d} | {m['tier']:10s} | {m['title'][:50]} @ {m.get('company','')[:20]}")
    print(f"         Location: {m['location'][:30]} | Source: {m['source']}")
    if matched_skills:
        print(f"         Matched: {matched_skills[:5]}")
    if missing:
        print(f"         Missing: {missing[:5]}")

# 9. Cover letter for top match
if matches:
    print("\n=== 9. COVER LETTER ===")
    job_id = matches[0]["id"]
    r = api("POST", f"/api/jobs/{job_id}/generate-cover-letter", {}, token=token)
    letter = r.get("cover_letter", "")
    print(f"Word count: {r.get('word_count', 0)}")
    print(letter[:500])
    print("...")

print("\n=== DONE ===")
