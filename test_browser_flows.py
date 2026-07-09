#!/usr/bin/env python3
"""
CareerPilot AI — Comprehensive Browser Flow Automation & E2E Verification Suite
================================================================================
Tests all critical browser cases through Next.js (:3000) and Caddy (:80):
  Case 1: Public HTML Loading (GET http://localhost:3000/)
  Case 2: Next.js API Proxy Rewrite (GET http://localhost:3000/api/health)
  Case 3: Caddy Reverse Proxy Access (GET http://localhost/api/health)
  Case 4: User Registration Flow via Browser Proxy (POST /api/auth/register)
  Case 5: Session Verification on Browser Mount (GET /api/auth/me with Bearer token)
  Case 6: Remember Me & Login Authentication Flow (POST /api/auth/login)
  Case 7: Protected Dashboard API Access (GET /api/dashboard/stats via :3000)
  Case 8: Job Listings Browser Request (GET /api/jobs via :3000)
  Case 9: Scraper & Process Status Check (GET /api/process-statuses via :3000)
  Case 10: Unauthorized / Expired Token Trigger (GET /api/auth/me with invalid token -> verifies HTTP 401 clean response)
  Case 11: Invalid Job ID UUID Resilience (GET /api/jobs/invalid-id -> verifies HTTP 404 clean response)
"""

import json
import random
import string
import sys
import urllib.error
import urllib.request

COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"


def print_case(case_num: int, title: str):
    print(f"\n{COLOR_BLUE}[Case {case_num}] {title}{COLOR_RESET}")


def pass_test(msg: str):
    print(f"  {COLOR_GREEN}✔ PASS:{COLOR_RESET} {msg}")


def fail_test(msg: str):
    print(f"  {COLOR_RED}✘ FAIL:{COLOR_RESET} {msg}")
    sys.exit(1)


def make_http(
    url: str,
    method: str = "GET",
    headers: dict = None,
    data: dict = None,
    timeout: int = 15,
):
    if headers is None:
        headers = {}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            try:
                json_data = json.loads(content.decode("utf-8"))
            except Exception:
                json_data = None
            return {
                "status": resp.status,
                "content": content.decode("utf-8", errors="ignore"),
                "json": json_data,
                "headers": dict(resp.headers),
            }
    except urllib.error.HTTPError as e:
        content = e.read()
        try:
            json_data = json.loads(content.decode("utf-8"))
        except Exception:
            json_data = None
        return {
            "status": e.code,
            "content": content.decode("utf-8", errors="ignore"),
            "json": json_data,
            "headers": dict(e.headers),
        }
    except Exception as e:
        return {"status": 0, "error": str(e), "content": "", "json": None}


def main():
    print("=" * 76)
    print("CAREERPILOT AI — BROWSER FLOW & END-TO-END VERIFICATION SUITE")
    print("=" * 76)

    # Generate random test account email
    rand_suffix = "".join(
        random.choices(string.ascii_lowercase + string.digits, k=6)
    )
    test_email = f"browser_test_{rand_suffix}@careerpilot.ai"
    test_pass = "BrowserTest123!"

    # --- Case 1: Public HTML Loading ---
    print_case(1, "Public HTML Entry Point (GET http://localhost:3000/)")
    res = make_http("http://localhost:3000/")
    if res["status"] == 200 and "<!DOCTYPE html>" in res["content"]:
        pass_test(
            f"Next.js HTML page loaded cleanly (HTTP 200, {len(res['content'])} bytes)"
        )
    else:
        fail_test(
            f"Failed to load frontend HTML: HTTP {res['status']} {res.get('error','')}"
        )

    # --- Case 2: Next.js API Proxy Rewrite ---
    print_case(2, "Next.js API Proxy Rewrite (GET http://localhost:3000/api/health)")
    res = make_http("http://localhost:3000/api/health")
    if res["status"] == 200 and res["json"] and res["json"].get("status") == "ok":
        pass_test("Frontend Next.js successfully proxies /api/health -> HTTP 200 OK")
    else:
        fail_test(
            f"Next.js API proxy health check failed: HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 3: Caddy Reverse Proxy ---
    print_case(3, "Caddy Reverse Proxy Check (GET http://localhost/api/health)")
    res = make_http("http://localhost/api/health")
    if res["status"] == 200 and res["json"] and res["json"].get("status") == "ok":
        pass_test("Caddy reverse proxy (:80) routes /api/health -> HTTP 200 OK")
    else:
        fail_test(
            f"Caddy health check failed: HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 4: Registration Flow ---
    print_case(4, "User Registration Flow via Browser Proxy (POST /api/auth/register)")
    res = make_http(
        "http://localhost:3000/api/auth/register",
        method="POST",
        data={
            "full_name": "Browser Tester",
            "email": test_email,
            "password": test_pass,
        },
    )
    if res["status"] == 201 and res["json"] and "access_token" in res["json"]:
        access_token = res["json"]["access_token"]
        pass_test(
            f"Registration successful for {test_email}. Received JWT access token."
        )
    else:
        fail_test(
            f"Registration failed: HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 5: Session Verification on Browser Mount ---
    print_case(5, "Session Verification on Application Mount (GET /api/auth/me)")
    res = make_http(
        "http://localhost:3000/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if res["status"] == 200 and res["json"] and res["json"].get("email") == test_email:
        pass_test("Session verified successfully via /api/auth/me -> HTTP 200 OK")
    else:
        fail_test(
            f"Session verification failed: HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 6: Login Flow ---
    print_case(6, "Remember Me & Login Authentication Flow (POST /api/auth/login)")
    res = make_http(
        "http://localhost:3000/api/auth/login",
        method="POST",
        data={"email": test_email, "password": test_pass},
    )
    if res["status"] == 200 and res["json"] and "access_token" in res["json"]:
        access_token = res["json"]["access_token"]
        pass_test("Login endpoint verified via Next.js proxy -> HTTP 200 OK")
    else:
        fail_test(f"Login failed: HTTP {res['status']} -> {res.get('content')}")

    # --- Case 7: Protected Dashboard API Access ---
    print_case(
        7,
        "Protected Dashboard Stats API (GET /api/dashboard/stats via :3000)",
    )
    res = make_http(
        "http://localhost:3000/api/dashboard/stats",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if res["status"] == 200 and res["json"] is not None:
        pass_test("Dashboard stats retrieved successfully -> HTTP 200 OK")
    else:
        fail_test(
            f"Dashboard stats call failed: HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 8: Job Listings Browser Request ---
    print_case(8, "Job Listings Browser Request (GET /api/jobs via :3000)")
    res = make_http(
        "http://localhost:3000/api/jobs",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if res["status"] == 200 and res["json"] and "data" in res["json"]:
        pass_test(
            f"Jobs listing retrieved successfully (Count: {res['json'].get('total', 0)}) -> HTTP 200 OK"
        )
    else:
        fail_test(
            f"Jobs listing call failed: HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 9: Process Status Check ---
    print_case(
        9,
        "Scraper & Process Status API Check (GET /api/process-statuses via :3000)",
    )
    res = make_http(
        "http://localhost:3000/api/process-statuses",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if res["status"] == 200 and res["json"] is not None:
        pass_test("Process status check succeeded -> HTTP 200 OK")
    else:
        fail_test(
            f"Process status check failed: HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 10: Unauthorized Token Trigger ---
    print_case(
        10,
        "Unauthorized Token Handling (GET /api/auth/me with invalid token -> expects 401)",
    )
    res = make_http(
        "http://localhost:3000/api/auth/me",
        headers={"Authorization": "Bearer invalid_expired_token_123"},
    )
    if res["status"] == 401:
        pass_test(
            "Invalid token correctly triggered HTTP 401 Unauthorized (ensuring clean client logout)"
        )
    else:
        fail_test(
            f"Expected HTTP 401 but got HTTP {res['status']} -> {res.get('content')}"
        )

    # --- Case 11: Invalid UUID Resilience ---
    print_case(
        11,
        "UUID Resilience Check (GET /api/jobs/not-a-uuid -> expects clean 404)",
    )
    res = make_http(
        "http://localhost:3000/api/jobs/not-a-uuid",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if res["status"] == 404:
        pass_test("Malformed non-UUID string cleanly returned HTTP 404 Not Found")
    else:
        fail_test(
            f"Expected HTTP 404 but got HTTP {res['status']} -> {res.get('content')}"
        )

    print("\n" + "=" * 76)
    print(f"{COLOR_GREEN}ALL 11 BROWSER END-TO-END VERIFICATION CASES PASSED!{COLOR_RESET}")
    print("=" * 76)


if __name__ == "__main__":
    main()
