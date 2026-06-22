#!/usr/bin/env python3
"""Full integration test for CareerPilot scraper system using localhost."""
import json, os, sys, time, requests

BASE = "http://localhost:7899"

def api(method, path, data=None, token=None, files=None):
    url = BASE + path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=60)
        elif method == "POST":
            if files:
                r = requests.post(url, headers=headers, files=files, timeout=60)
            else:
                r = requests.post(url, headers=headers, json=data, timeout=60)
        else:
            raise ValueError(f"Unsupported method {method}")
        
        if r.status_code >= 400:
            return {"error": r.status_code, "body": r.text}
        return r.json()
    except Exception as e:
        return {"error": "exception", "body": str(e)}

# 1. Login (user may already exist)
# Demo credentials
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
pdf_content = b"%PDF-1.4\n%EOF\nJohn Doe\nSoftware Engineer\nSkills: Python, Docker, Kubernetes, AWS, Linux, Git, CI/CD, PostgreSQL"
files = {'file': ('example_resume.pdf', pdf_content, 'application/pdf')}
r = api("POST", "/api/resumes/upload", token=token, files=files)
print(f"  Resume upload: {json.dumps(r, indent=2)[:200]}")

# 3. Scraper status
print("\n=== 3. SCRAPER STATUS ===")
r = api("GET", "/api/scraper/status", token=token)
print(json.dumps(r, indent=2))

# 4. Trigger scrape
print("\n=== 4. TRIGGER SCRAPE ===")
r = api("POST", "/api/scraper/trigger", {}, token=token)
print(f"  Task: {r.get('task_id','?')[:20]}... Status: {r.get('status')}")

# 5. Wait for scrape
print("\n=== 5. WAITING FOR SCRAPE ===")
for i in range(10):
    time.sleep(5)
    r = api("GET", "/api/scraper/status", token=token)
    total = r.get("total_jobs", 0)
    linkedin = r.get("linkedin_jobs", 0)
    naukri = r.get("naukri_jobs", 0)
    print(f"  Poll {i+1}: total={total} li={linkedin} nauk={naukri}")
    if total > 0:
        print("  Scraper populated some jobs!")
        break

# 6. Run scoring
print("\n=== 6. TRIGGER SCORING ===")
r = api("POST", "/api/scraper/score-jobs", {}, token=token)
print(f"  Scoring: {json.dumps(r, indent=2)[:200]}")

# 7. Wait for scoring
print("\n=== 7. WAITING FOR SCORING ===")
for i in range(10):
    time.sleep(3)
    r = api("GET", "/api/scraper/status", token=token)
    matched = r.get("matched_jobs", 0)
    print(f"  Poll {i+1}: {matched} matched jobs")
    if matched > 0:
        break

# 8. Get matches
print("\n=== 8. TOP MATCHES ===")
r = api("GET", "/api/jobs/matches?min_score=1&limit=10", token=token)
matches = r.get("matches", [])
print(f"Total matches: {r.get('count', 0)}")
for m in matches[:5]:
    matched_skills = m.get("matched_skills", [])
    missing = m.get("missing_skills", [])
    print(f"  {m['relevance_score']:5d} | {m['tier']:10s} | {m['title'][:50]} @ {m.get('company','')[:20]}")
    print(f"         Location: {m['location'][:30]} | Source: {m['source']}")

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
