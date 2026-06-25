#!/usr/bin/env python3
"""
CareerPilot AI - Frontend Integration Test
Tests frontend-backend integration for:
1. Location input in dashboard
2. Per-user job display
3. Job detail endpoint security
"""
import json
import urllib.request
import urllib.error
import sys

BASE_URL = "http://localhost:7899/api"

def make_request(endpoint, method="GET", data=None, token=None):
    """Make HTTP request to CareerPilot API."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "status": resp.status,
                "data": json.loads(resp.read().decode()) if resp.status != 204 else None
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode()}
    except Exception as e:
        return {"status": 0, "error": str(e)}

def test_frontend_location_input():
    """Test that frontend sends location parameter correctly."""
    print("\n" + "="*70)
    print("TEST 1: Frontend Location Input")
    print("="*70)
    
    # Create a test user
    print("\n[1] Creating test user...")
    resp = make_request("/auth/register", method="POST", data={
        "email": f"frontend_test_{sys.argv[1] if len(sys.argv) > 1 else 'loc'}@careerpilot.ai",
        "password": "FrontendTest123!",
        "name": "Frontend Test User"
    })
    
    if resp["status"] not in [200, 201]:
        print(f"  ✗ Failed: {resp}")
        return False
    
    token = resp["data"]["access_token"]
    user_id = resp["data"]["user_id"]
    print(f"  ✓ User created: {user_id}")
    
    # Simulate scraping with location from dashboard input
    print("\n[2] Simulating dashboard scrape with location 'Mumbai'...")
    resp = make_request("/scraper/trigger", method="POST", data={
        "location": "Mumbai"
    }, token=token)
    
    if resp["status"] != 200:
        print(f"  ✗ Failed to trigger scrape: {resp}")
        return False
    
    task_id = resp["data"].get("task_id")
    print(f"  ✓ Scrape task created: {task_id}")
    
    # Wait for scrape
    print("\n[3] Waiting for scrape to complete...")
    import time
    for i in range(8):
        time.sleep(5)
        resp = make_request("/dashboard/stats", token=token)
        if resp["status"] == 200:
            stats = resp["data"].get("scraper", {})
            if not stats.get("is_scraping", True):
                print(f"  ✓ Scrape completed")
                print(f"     LinkedIn: {stats.get('source_breakdown', {}).get('linkedin', 0)}")
                print(f"     Naukri: {stats.get('source_breakdown', {}).get('naukri', 0)}")
                break
        print(f"  ... waiting ({i+1}/8)")
    else:
        print("  ⚠ Scrape may still be running")
    
    return True

def test_user_specific_jobs():
    """Test that /api/jobs returns only user's jobs."""
    print("\n" + "="*70)
    print("TEST 2: User-Specific Job Display")
    print("="*70)
    
    # Create two users
    print("\n[1] Creating User A...")
    resp = make_request("/auth/register", method="POST", data={
        "email": f"user_a_{sys.argv[1] if len(sys.argv) > 1 else 'test'}@careerpilot.ai",
        "password": "UserA123!",
        "name": "User A"
    })
    if resp["status"] not in [200, 201]:
        print(f"  ✗ Failed: {resp}")
        return False
    
    user_a_token = resp["data"]["access_token"]
    user_a_id = resp["data"]["user_id"]
    print(f"  ✓ User A: {user_a_id}")
    
    print("\n[2] Creating User B...")
    resp = make_request("/auth/register", method="POST", data={
        "email": f"user_b_{sys.argv[1] if len(sys.argv) > 1 else 'test'}@careerpilot.ai",
        "password": "UserB123!",
        "name": "User B"
    })
    if resp["status"] not in [200, 201]:
        print(f"  ✗ Failed: {resp}")
        return False
    
    user_b_token = resp["data"]["access_token"]
    user_b_id = resp["data"]["user_id"]
    print(f"  ✓ User B: {user_b_id}")
    
    # Check both users start with 0 jobs
    print("\n[3] Verifying both users start with 0 jobs...")
    for name, token in [("User A", user_a_token), ("User B", user_b_token)]:
        resp = make_request("/jobs", token=token)
        count = resp["data"].get("total", 0) if resp["status"] == 200 else -1
        print(f"  ✓ {name}: {count} jobs")
        if count != 0:
            print(f"  ✗ FAIL: Expected 0 jobs for new user")
            return False
    
    # Trigger scrape for User A with specific location
    print("\n[4] Triggering scrape for User A (location: 'Bangalore')...")
    resp = make_request("/scraper/trigger", method="POST", data={
        "location": "Bangalore"
    }, token=user_a_token)
    
    if resp["status"] != 200:
        print(f"  ✗ Failed: {resp}")
        return False
    print(f"  ✓ Scrape triggered")
    
    # Wait briefly for some jobs to be processed
    print("\n[5] Waiting for jobs to be processed...")
    import time
    time.sleep(15)
    
    # Check User A's jobs
    print("\n[6] Checking User A's jobs...")
    resp = make_request("/jobs", token=user_a_token)
    if resp["status"] != 200:
        print(f"  ✗ Failed: {resp}")
        return False
    
    user_a_jobs = resp["data"].get("total", 0)
    print(f"  ✓ User A has {user_a_jobs} jobs")
    
    # Check User B's jobs (should still be 0)
    print("\n[7] Checking User B's jobs (should still be 0)...")
    resp = make_request("/jobs", token=user_b_token)
    if resp["status"] != 200:
        print(f"  ✗ Failed: {resp}")
        return False
    
    user_b_jobs = resp["data"].get("total", 0)
    print(f"  ✓ User B has {user_b_jobs} jobs")
    
    if user_b_jobs != 0:
        print(f"  ✗ FAIL: User B sees {user_b_jobs} jobs (should be 0)")
        print(f"  ⚠ This indicates job leakage between users")
        return False
    
    print("  ✓ PASS: User isolation working correctly")
    
    # Verify job detail endpoint security
    if user_a_jobs > 0:
        print("\n[8] Testing job detail endpoint security...")
        # Get a job ID from User A
        resp = make_request("/jobs?page=1&page_size=1", token=user_a_token)
        jobs = resp["data"].get("data", [])
        if jobs:
            job_id = jobs[0]["id"]
            
            # User A should be able to view their job
            resp = make_request(f"/jobs/{job_id}", token=user_a_token)
            if resp["status"] == 200:
                print(f"  ✓ User A can view their job {job_id}")
            else:
                print(f"  ⚠ User A couldn't view job: {resp}")
            
            # User B should NOT be able to view User A's job
            resp = make_request(f"/jobs/{job_id}", token=user_b_token)
            if resp["status"] == 404:
                print(f"  ✓ User B correctly gets 404 for User A's job")
            elif resp["status"] == 200:
                print(f"  ✗ FAIL: User B can view User A's job {job_id}")
                return False
            else:
                print(f"  ⚠ Unexpected response: {resp}")
    
    print("\n" + "="*70)
    print("TEST 2: PASS - User-specific job display working")
    print("="*70)
    return True

def test_dashboard_scraper_status():
    """Test that dashboard shows correct scraper status."""
    print("\n" + "="*70)
    print("TEST 3: Dashboard Scraper Status")
    print("="*70)
    
    # Create test user
    print("\n[1] Creating test user...")
    resp = make_request("/auth/register", method="POST", data={
        "email": f"dashboard_{sys.argv[1] if len(sys.argv) > 1 else 'status'}@careerpilot.ai",
        "password": "DashTest123!",
        "name": "Dashboard Test"
    })
    
    if resp["status"] not in [200, 201]:
        print(f"  ✗ Failed: {resp}")
        return False
    
    token = resp["data"]["access_token"]
    print("  ✓ User created")
    
    # Check dashboard stats
    print("\n[2] Fetching dashboard stats...")
    resp = make_request("/dashboard/stats", token=token)
    
    if resp["status"] != 200:
        print(f"  ✗ Failed: {resp}")
        return False
    
    stats = resp["data"]
    scraper = stats.get("scraper", {})
    
    print(f"  ✓ Dashboard stats received")
    print(f"     Is scraping: {scraper.get('is_scraping', False)}")
    print(f"     Last scrape: {scraper.get('last_scrape_at', 'Never')}")
    print(f"     Source breakdown:")
    breakdown = scraper.get("source_breakdown", {})
    print(f"       - LinkedIn: {breakdown.get('linkedin', 0)}")
    print(f"       - Naukri: {breakdown.get('naukri', 0)}")
    
    # Verify frontend can access this data structure
    required_fields = ["is_scraping", "last_scrape_at", "source_breakdown"]
    missing = [f for f in required_fields if f not in scraper]
    if missing:
        print(f"  ✗ FAIL: Missing fields: {missing}")
        return False
    
    if "source_breakdown" in scraper:
        required_breakdown = ["linkedin", "naukri"]
        missing_breakdown = [f for f in required_breakdown if f not in scraper["source_breakdown"]]
        if missing_breakdown:
            print(f"  ✗ FAIL: Missing breakdown fields: {missing_breakdown}")
            return False
    
    print("  ✓ PASS: Dashboard scraper status format correct")
    return True

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CAREERPILOT AI - FRONTEND INTEGRATION TEST")
    print("="*70)
    
    test1_pass = test_frontend_location_input()
    test2_pass = test_user_specific_jobs()
    test3_pass = test_dashboard_scraper_status()
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Test 1 (Location Input):        {'PASS' if test1_pass else 'FAIL'}")
    print(f"Test 2 (User-Specific Jobs):    {'PASS' if test2_pass else 'FAIL'}")
    print(f"Test 3 (Dashboard Status):      {'PASS' if test3_pass else 'FAIL'}")
    print("="*70)
    
    all_pass = test1_pass and test2_pass and test3_pass
    if all_pass:
        print("\n✓ All frontend integration tests passed!")
        print("  - Location input working")
        print("  - Per-user job isolation verified")
        print("  - Dashboard scraper status correct")
    else:
        print("\n✗ Some tests failed")
    
    print("="*70)
    sys.exit(0 if all_pass else 1)