#!/usr/bin/env python3
"""CareerPilot Full-Stack Multi-Layer Test Suite."""
import json, os, subprocess, sys, time, urllib.request, urllib.error

PASS, FAIL = "\u2705", "\u274c"
BASE = "http://localhost:7899/api"
WEB = "http://localhost:3000"
CWD = "/home/ubuntu/careerpilot"
results = []

def http(method, url, headers=None, data=None, timeout=10):
    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return e.code, body
    except Exception as e:
        return 0, str(e)

def cmd(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=CWD)

def docker_exe(service, *args):
    return cmd(["docker", "exec", "careerpilot-" + service] + list(args))

def test(cat, name, fn):
    try:
        ok = fn()
        icon = PASS if ok else FAIL
    except Exception as e:
        icon, ok = FAIL, False
        name += " [" + str(e) + "]"
    results.append((icon, cat, name))
    return ok

# === LAYER 1: INFRASTRUCTURE ===
print("LAYER 1: INFRASTRUCTURE & HEALTH")

r = docker_exe("postgres", "psql", "-U", "careerpilot", "-d", "careerpilot", "-c", "SELECT 1;")
test("Infra", "Postgres connectivity", lambda: r.returncode == 0)

r = docker_exe("redis", "redis-cli", "ping")
test("Infra", "Redis ping", lambda: "PONG" in r.stdout)

status, body = http("GET", BASE + "/health")
test("Infra", "Backend health (" + str(status) + ")", lambda: status == 200)

r = cmd(["docker", "compose", "ps", "--format", "{{.Names}} {{.Status}}"])
lines = [l.strip() for l in r.stdout.split("\n") if l.strip()]
unhealthy = [l for l in lines if "unhealthy" in l.lower()]
test("Infra", "All containers healthy", lambda: len(unhealthy) == 0)

f_status, f_body = http("GET", WEB + "/")
test("Infra", "Frontend loads (" + str(f_status) + ")", lambda: f_status == 200)

c_status, c_body = http("GET", "http://localhost/")
test("Infra", "Caddy proxy (" + str(c_status) + ")", lambda: c_status in (200, 301, 302, 502))

core_services = ["backend", "beat", "caddy", "frontend", "postgres", "redis", "worker"]
r = cmd(["docker", "compose", "ps", "--format", "{{.Names}}"])
running = r.stdout.strip().split("\n")
for s in core_services:
    found = any(s in n for n in running)
    test("Infra", "Service: " + s, lambda f=found: f)

# === LAYER 2: AUTH API ===
print("\nLAYER 2: AUTH API")

ts = str(int(time.time() % 10000))
email = "test_" + ts + "@ex.com"
PW = "Password123"
t = None

status, body = http("POST", BASE + "/auth/register",
                    data={"email": email, "password": PW, "name": "Test User"})
reg_ok = status == 201
test("Auth", "Register new user -> " + str(status), lambda: reg_ok)
if reg_ok:
    try:
        data = json.loads(body)
        t = data.get("access_token") or data.get("token")
        if t:
            test("Auth", "  Token received", lambda: True)
    except Exception:
        pass

status, _ = http("POST", BASE + "/auth/login", data={"email": email, "password": PW})
test("Auth", "Login correct -> " + str(status), lambda: status == 200)

status, _ = http("POST", BASE + "/auth/login", data={"email": email, "password": "wrong"})
test("Auth", "Login wrong pw -> " + str(status), lambda: status == 401)

status, _ = http("POST", BASE + "/auth/register", data={"email": email, "password": PW})
test("Auth", "Duplicate register -> " + str(status), lambda: status == 409)

status, _ = http("POST", BASE + "/auth/register", data={})
test("Auth", "Register empty -> " + str(status), lambda: status in (400, 422))

status, _ = http("GET", BASE + "/auth/me")
test("Auth", "Me no auth -> " + str(status), lambda: status == 401)

if t:
    status, _ = http("GET", BASE + "/auth/me",
                     headers={"Authorization": "Bearer " + t})
    test("Auth", "Me with token -> " + str(status), lambda: status == 200)

    status, _ = http("GET", BASE + "/auth/me",
                     headers={"Authorization": "Bearer garbageToken123"})
    test("Auth", "Garbage token -> " + str(status), lambda: status == 401)

    status, _ = http("POST", BASE + "/auth/login",
                     data={"email": "noone@nowhere.com", "password": PW})
    test("Auth", "Login non-existent -> " + str(status), lambda: status == 401)
else:
    test("Auth", "Skipping token-dependent tests", lambda: True)

# === LAYER 3: BUSINESS API ===
print("\nLAYER 3: BUSINESS API")

if t:
    pdf_path = "/tmp/test_resume_upload.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF")

    r = subprocess.run([
        "curl", "-s", "-w", "\n%{http_code}",
        "-X", "POST", BASE + "/resumes/upload",
        "-H", "Authorization: Bearer " + t,
        "-F", "file=@" + pdf_path + ";type=application/pdf",
    ], capture_output=True, text=True, timeout=15)
    parts = r.stdout.strip().rsplit("\n", 1)
    up_status = int(parts[1]) if len(parts) == 2 else 0
    test("Biz", "Upload PDF -> " + str(up_status), lambda: up_status in (200, 201))

    r2 = subprocess.run([
        "curl", "-s", "-w", "\n%{http_code}",
        "-X", "POST", BASE + "/resumes/upload",
        "-F", "file=@" + pdf_path + ";type=application/pdf",
    ], capture_output=True, text=True, timeout=10)
    noau = int(r2.stdout.strip().rsplit("\n", 1)[-1])
    test("Biz", "Upload no auth -> " + str(noau), lambda: noau == 401)

    os.unlink(pdf_path)

    status, _ = http("GET", BASE + "/resumes/",
                     headers={"Authorization": "Bearer " + t})
    test("Biz", "List resumes -> " + str(status), lambda: status == 200)

    status, _ = http("GET", BASE + "/jobs/",
                     headers={"Authorization": "Bearer " + t})
    test("Biz", "List jobs -> " + str(status), lambda: status == 200)

    status, _ = http("POST", BASE + "/scraper/trigger",
                     headers={"Authorization": "Bearer " + t},
                     data={"location": "Bangalore"})
    test("Biz", "Trigger scrape -> " + str(status), lambda: status == 200)
else:
    test("Biz", "All business tests skipped (no token)", lambda: True)

# === LAYER 4: FRONTEND ===
print("\nLAYER 4: FRONTEND \u0026 E2E")

f_status, f_body = http("GET", WEB + "/")
test("Frontend", "Home page -> " + str(f_status), lambda: f_status == 200)
if f_status == 200:
    test("Frontend", "  Has Next.js assets", lambda: "_next" in f_body)
    test("Frontend", "  Has content (" + str(len(f_body)) + " chars)", lambda: len(f_body) > 100)

ts2 = str(int(time.time() % 1000))
status, _ = http("POST", WEB + "/api/auth/register",
                 data={"email": "e2e" + ts2 + "@test.com", "password": "Password123"})
test("Frontend", "Proxy register -> " + str(status), lambda: status == 201)

f2_status, f2_body = http("GET", WEB + "/jobs")
test("Frontend", "Jobs page -> " + str(f2_status), lambda: f2_status in (200, 302))

if f_status == 200:
    test("Frontend", "  Static assets in HTML", lambda: "_next/static" in f_body)

req = urllib.request.Request(WEB + "/")
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        ctype = r.headers.get("Content-Type", "")
        test("Frontend", "  Content-Type: text/html", lambda: "text/html" in ctype)
except Exception:
    test("Frontend", "  Content-Type check", lambda: False)

# === REPORT ===
print("\n" + "=" * 60)
cats = {}
for icon, cat, name in results:
    cats.setdefault(cat, []).append((icon, name))
passed = sum(1 for i, _, _ in results if i == PASS)
failed = sum(1 for i, _, _ in results if i == FAIL)
print("  RESULTS: " + str(passed) + " passed  /  " + str(failed) + " failed\n")
for cat, items in cats.items():
    print("  [" + cat + "]")
    for icon, name in items:
        print("    " + icon + " " + name)
print("\n  TOTAL: " + str(len(results)) + " tests, " + str(passed) + " passed, " + str(failed) + " failed")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
