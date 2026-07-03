#!/usr/bin/env python3
"""
CareerPilot — Full Pipeline Test Script
Run this to verify: scrape -> resume upload -> match pipeline
"""
import urllib.request
import urllib.error
import json
import time

BASE = "http://3.109.213.250"

def api(method, path, body=None, headers=None):
    url = f"{BASE}{path}"
    req_headers = headers or {}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return -1, {"error": str(e)}

def main():
    print("=== CareerPilot Pipeline Test ===\n")

    # 1. Login
    print("[1/5] Login...")
    status, resp = api("POST", "/api/auth/login",
        {"email": "subham@example.com", "password": "test123456"},
        {"Content-Type": "application/json"})
    if status != 200:
        print(f"  FAILED: {resp}")
        return
    token = resp["access_token"]
    print("  OK — token obtained")

    auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Jobs in DB
    print("\n[2/5] Jobs in DB...")
    status, resp = api("GET", "/api/jobs", headers=auth)
    if status == 200:
        print(f"  OK — {resp.get('total', 0)} jobs found")
    else:
        print(f"  WARN: {status}")

    # 3. Trigger scrape
    print("\n[3/5] Trigger scrape (India)...")
    status, resp = api("POST", "/api/scraper/trigger",
        {"linkedin_queries": [], "naukri_queries": ["software engineer"], "location": "India"},
        auth)
    if status in (200, 202):
        print(f"  OK — {resp.get('status', 'queued')}")
    else:
        print(f"  WARN: HTTP {status}")

    # 4. Trigger re-rank
    print("\n[4/5] Trigger re-rank...")
    status, resp = api("POST", "/api/matches/re-rank", {}, auth)
    if status in (200, 202):
        print(f"  OK — {resp.get('status', 'started')}")
    else:
        print(f"  WARN: HTTP {status}")

    # Wait for background job
    print("\n  Waiting 10s for background matching...")
    time.sleep(10)

    # 5. Check matches
    print("\n[5/5] Check matches...")
    status, resp = api("GET", "/api/matches/", headers=auth)
    if status == 200:
        total = resp.get("total", 0)
        print(f"  OK — {total} matches")
        for m in resp.get("matches", [])[:3]:
            print(f"    - {m.get('job_title','?')} @ {m.get('company_name','?')}: {m.get('match_score','?')}")
    else:
        print(f"  FAIL: HTTP {status} — {resp}")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
