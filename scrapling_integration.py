#!/usr/bin/env python3
"""
CareerPilot -> LinkedIn job discovery (resume-matched, Telegram delivery).

Why LinkedIn is the engine:
  * LinkedIn's guest search is query-aware and returns clean, role-targeted
    cards when driven with the resume's target-role queries.
  * Naukri's public API (and the Scrapling Fetcher hitting it) returns the
    SAME ~20 unrelated jobs (HR Executive, Optometrist, Area Sales Manager)
    regardless of the query string from this datacenter IP, so it contributes
    zero relevant matches. The keyless APIs (remotive/themuse/arbeitnow) ignore
    queries entirely (cashiers/writers). Both are therefore dropped.

Relevance model (resume = subham_hirani_resume.txt):
  1. STRICT GATE: a job must match a positive network/infra/sysadmin/security/
     cloud/devops/support title regex (or have strong skill overlap) AND must
     not match an off-target role (sales, finance, law, VLSI/electrical,
     medical, HR, software dev, ...).
  2. SCORE = best title-relevance weight + min(30, skill_overlap*2) + location
     tier (Gujarat +10 > Remote +6 > India +4 > International +2). Location is
     intentionally a tiebreaker, not a dominator, so a Gujarat "IT Support"
     never outranks a pan-India "Network Engineer".
  3. DAILY FRESH: jobs already delivered in any prior run are excluded (tracked
     in artifacts/scraped_history.jsonl), so the report only lists NEW postings.
  4. HISTORY: every run writes a timestamped report + JSON snapshot; old runs
     are never overwritten.
  5. APPLY: the LinkedIn job URL is the direct-apply link (Easy Apply / external
     ATS). NOTE: LinkedIn's free guest data exposes NO recruiter/employer email,
     so Gmail IDs are not available — use `--fetch-emails` (best-effort, off by
     default) to attempt extraction from each job's detail page.
  6. Top 50 fresh jobs are delivered to the LIVE Telegram gateway (reads .env).

Run:
  /home/ubuntu/scrapling-venv/bin/python /home/ubuntu/careerpilot/scrapling_integration.py
  .../scrapling_integration.py --dry-run            # rank only, no Telegram
  .../scrapling_integration.py --use-cache          # reuse last raw scrape
  .../scrapling_integration.py --fetch-emails       # best-effort apply-email harvest
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/ubuntu/careerpilot/backend/app/agents")
from multi_portal_scraper import LinkedInGuestScraper, JobPosting  # noqa: E402

import httpx  # noqa: E402

ROOT = "/home/ubuntu/careerpilot"
ENV_PATH = os.path.join(ROOT, ".env")
ART = os.path.join(ROOT, "artifacts")
CACHE_PATH = os.path.join(ART, "cache_scrapling.json")
HISTORY_PATH = os.path.join(ART, "scraped_history.jsonl")
os.makedirs(ART, exist_ok=True)

# Resume-targeted role queries (drives LinkedIn, which honors them).
# Broadened set so a thin daily market still yields 50+ relevant matches.
ROLE_QUERIES = [
    "network engineer", "system administrator", "infrastructure engineer",
    "devops engineer", "cloud engineer", "security analyst",
    "network administrator", "it support", "technical support",
    "windows administrator", "soc analyst", "linux administrator",
    "it operations", "service desk", "desktop support",
    "technical support engineer", "network operations", "aws administrator",
    "cloud administrator", "help desk", "l2 support", "l1 support",
    "system engineer", "it administrator", "windows server",
    "cyber security", "information technology",
]
LOCATION = "Ahmedabad, Gujarat"

# ---- Relevance gating ----
POSITIVE_TITLE = [
    r"network\s*eng", r"network\s*admin", r"network\s*ops", r"network\s*tech",
    r"network\s*operations", r"network\s*operations\s*center", r"\bnoc\b\s*(engineer|analyst|admin|technician|operator|specialist|lead|manager)", r"network\s*operations\s*centre", r"network\s*specialist",
    r"network\s*consultant", r"jr\.?\s*network", r"junior\s*network",
    r"associate\s*network", r"graduate\s*network", r"l1\s*network",
    r"l2\s*network", r"network\s*engineer\s*trainee",
    r"infrastructure", r"system\s*admin", r"sysadmin", r"windows\s*admin",
    r"linux\s*admin", r"server\s*admin", r"active\s*directory",
    r"domain\s*admin", r"security\s*analyst", r"soc\s*analyst", r"siem",
    r"cyber\s*sec", r"information\s*security", r"it\s*security",
    r"security\s*eng", r"security\s*operations",
    r"devops", r"cloud\s*eng", r"cloud\s*infra", r"cloud\s*ops",
    r"site\s*reliability", r"\bsre\b", r"platform\s*eng",
    r"system\s*eng", r"system\s*engineer", r"virtuali[sz]ation",
    r"vmware\s*admin", r"hyper.?v", r"windows\s*server", r"linux\s*engineer",
    r"support\s*eng", r"it\s*support", r"tech(nical)?\s*support",
    r"help\s*desk", r"desktop\s*support", r"service\s*desk", r"it\s*helpdesk",
    r"it\s*administrator", r"it\s*admin", r"it\s*operations",
    r"it\s*executive", r"it\s*associate", r"it\s*infrastructure",
]
NEGATIVE_TITLE = [
    r"sales", r"business\s*development", r"\bbdm\b", r"marketing", r"\bloan\b",
    r"accountant", r"accounting", r"finance", r"audit", r"\btax\b",
    r"chartered", r"\blaw\b", r"legal", r"ip\s*and\s*corporate",
    r"\bhr\b", r"recruitment", r"talent", r"payroll", r"\bsap\b", r"fico",
    r"\berp\b", r"oracle\s*apps", r"abap", r"doctor", r"nurse", r"physician",
    r"therapist", r"medical", r"pharma", r"teacher", r"faculty", r"professor",
    r"tutor", r"content", r"writer", r"copywriter", r"civil",
    r"mechanical", r"electrical", r"structural", r"embedded", r"firmware",
    r"vlsi", r"asic", r"\brtl\b", r"semiconductor", r"\bchip\b",
    r"design\s*engineer", r"physical\s*design", r"frontend", r"front-end",
    r"backend", r"back-end", r"full\s*stack", r"software\s*engineer",
    r"web\s*developer", r"data\s*scientist", r"\bml\s*engineer\b",
]
POS_RX = [re.compile(r, re.I) for r in POSITIVE_TITLE]
NEG_RX = [re.compile(r, re.I) for r in NEGATIVE_TITLE]

# Resume skills (from subham_hirani_resume.txt) for overlap scoring.
RESUME_SKILLS = [
    "windows server", "active directory", "ad ds", "group policy", "gpo",
    "dns", "dhcp", "rras", "hyper-v", "iis", "docker", "kubernetes", "aws",
    "ec2", "vpc", "iam", "s3", "linux", "ubuntu", "centos", "rhel", "vlan",
    "ospf", "routing", "switching", "subnet", "vpn", "firewall", "siem",
    "wazuh", "soc", "backup", "disaster recovery", "dr", "network", "tcp/ip",
    "wireshark", "ci/cd", "terraform", "ansible", "nginx", "monitoring",
    "grafana", "prometheus", "ssh", "bash", "powershell", "gitlab", "gitea",
    "filezilla", "restic", "kopia", "uptime kuma", "n8n", "task scheduler",
    "vmware",
]
GUJ_CITIES = ["ahmedabad", "gandhinagar", "gift city", "vadodara", "baroda",
              "surat", "rajkot", "gujarat"]

# Title relevance weights (best match wins, not summed).
TITLE_W = [
    (re.compile(r"network\s*eng|network\s*admin|network\s*ops|network\s*tech|\bnoc\b|network\s*specialist", re.I), 30),
    (re.compile(r"infrastructure", re.I), 26),
    (re.compile(r"system\s*admin|sysadmin|windows\s*admin|linux\s*admin|server\s*admin|domain\s*admin|active\s*directory|it\s*admin|it\s*administrator", re.I), 25),
    (re.compile(r"security\s*analyst|soc\s*analyst|siem|cyber\s*sec|information\s*security|it\s*security|security\s*eng|security\s*operations", re.I), 24),
    (re.compile(r"devops|cloud\s*eng|cloud\s*infra|cloud\s*ops|site\s*reliability|\bsre\b|platform\s*eng|aws\s*admin|cloud\s*admin", re.I), 22),
    (re.compile(r"system\s*eng|system\s*engineer|virtuali[sz]ation|vmware\s*admin|hyper.?v|windows\s*server|linux\s*engineer", re.I), 20),
    (re.compile(r"support\s*eng|it\s*support|tech(nical)?\s*support|help\s*desk|desktop\s*support|service\s*desk|it\s*helpdesk", re.I), 18),
    (re.compile(r"it\s*operations|it\s*executive|it\s*associate|it\s*infrastructure", re.I), 17),
]

# Emails that are never a real application contact.
EMAIL_NOISE = re.compile(r"(linkedin|example|noreply|no-reply|donotreply|careers@|jobs@|do-not-reply|notification)", re.I)


def job_key(j: JobPosting) -> str:
    """Stable identity: LinkedIn job id when present, else title||company."""
    m = re.search(r"/jobs/view/(\d+)", j.url or "")
    if m:
        return f"li:{m.group(1)}"
    return re.sub(r"\s+", " ", f"{j.title}||{j.company}".lower()).strip()


def _blob(j: JobPosting) -> str:
    return " ".join([j.description or "", " ".join(j.skills or []),
                     j.title or "", j.company or ""]).lower()


def is_relevant(j: JobPosting) -> bool:
    t = j.title or ""
    if any(rx.search(t) for rx in POS_RX):
        return True
    if any(rx.search(t) for rx in NEG_RX):
        return False
    return sum(1 for k in RESUME_SKILLS if k in _blob(j)) >= 3


def loc_tier(j: JobPosting) -> int:
    loc = (j.location or "").lower()
    b = f"{j.location} {j.title}".lower()
    if any(c in b for c in GUJ_CITIES):
        return 10
    if "remote" in loc or "work from home" in loc or "wfh" in loc:
        return 6
    if "india" in loc or any(x in loc for x in ["ahmedabad", "gandhinagar", "gujarat", "surat", "pune", "mumbai", "bangalore", "bengaluru", "hyderabad", "delhi", "noida", "chennai"]):
        return 4
    if loc and loc not in ("", "worldwide"):
        return 2
    return 0


def score(j: JobPosting) -> int:
    t = j.title or ""
    s_title = 0
    for rx, w in TITLE_W:
        if rx.search(t):
            s_title = max(s_title, w)
    blob = _blob(j)
    s_skill = min(30, sum(1 for k in RESUME_SKILLS if k in blob) * 2)
    return s_title + s_skill + loc_tier(j)


# ---- History (cross-run dedup) ----
def load_history() -> dict:
    hist: dict = {}
    if os.path.exists(HISTORY_PATH):
        for line in open(HISTORY_PATH, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                hist[rec["key"]] = rec
            except Exception:
                continue
    return hist


def seed_history_from_reports(hist: dict) -> int:
    """Backfill history from any previously-delivered report/JSON snapshots
    so jobs we already sent are not re-sent. Returns count added."""
    added = 0
    for fn in sorted(os.listdir(ART)):
        path = os.path.join(ART, fn)
        if fn.startswith("job_report_") and fn.endswith("_scrapling.md"):
            txt = open(path, encoding="utf-8").read()
            for m in re.finditer(r"^\|\s*\d+\s*\|\s*\d+\s*\|\s*(.+?)(?:\s*🟢GUJ)?\s*\|\s*(.+?)\s*\|\s*.+?\s*\|\s*\S+\s*\|\s*\[link\]\((.+?)\)\s*\|", txt, re.M):
                title, company, url = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
                key = re.sub(r"\s+", " ", f"{title}||{company}".lower())
                if key not in hist:
                    hist[key] = {"key": key, "title": title, "company": company,
                                 "url": url, "first_seen": "seeded"}
                    added += 1
        elif fn.startswith("top50_") and fn.endswith("_scrapling.json"):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except Exception:
                continue
            for d in data:
                title, company, url = d.get("title", ""), d.get("company", ""), d.get("url", "")
                key = re.sub(r"\s+", " ", f"{title}||{company}".lower())
                if key not in hist:
                    hist[key] = {"key": key, "title": title, "company": company,
                                 "url": url, "first_seen": "seeded"}
                    added += 1
    return added


def append_history(records: list[dict]) -> None:
    if not records:
        return
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---- Best-effort apply-email harvest (opt-in) ----
async def fetch_apply_email(url: str) -> str:
    """Attempt to find a real application email on the job detail page.
    LinkedIn free pages almost never expose one (returns '')."""
    try:
        async with LinkedInGuestScraper()._client() as client:
            r = await client.get(url)
            r.raise_for_status()
            text = r.text
    except Exception:
        return ""
    found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    for e in found:
        if not EMAIL_NOISE.search(e):
            return e
    return ""


# ---- Telegram delivery (reads .env, never prints creds) ----
def load_env(path: str) -> dict:
    env = {}
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


def send_to_telegram(text: str, doc_path: str) -> bool:
    env = load_env(ENV_PATH)
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = env.get("TELEGRAM_ALLOWED_USER_ID", "").strip()
    if not token or not chat:
        print("Telegram: missing creds in .env — skipping delivery")
        return False
    base = f"https://api.telegram.org/bot{token}"
    with httpx.Client(timeout=40.0) as client:
        r = client.post(f"{base}/sendMessage",
                        json={"chat_id": chat, "text": text, "parse_mode": "Markdown"})
        print(f"Telegram sendMessage: ok={r.json().get('ok')} mid={r.json().get('result', {}).get('message_id')}")
        if not r.json().get("ok"):
            return False
        with open(doc_path, "rb") as d:
            r2 = client.post(f"{base}/sendDocument",
                             data={"chat_id": chat, "caption": "CareerPilot — fresh resume-matched jobs (top 50)"},
                             files={"document": ("report.md", d, "text/markdown")})
            print(f"Telegram sendDocument: ok={r2.json().get('ok')} mid={r2.json().get('result', {}).get('message_id')}")
        return r2.json().get("ok", False)


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print ranking to stdout only; do NOT send Telegram.")
    ap.add_argument("--use-cache", action="store_true",
                    help="Reuse artifacts/cache_scrapling.json; skip live scrape.")
    ap.add_argument("--fetch-emails", action="store_true",
                    help="Best-effort: try to harvest an apply email per job (slow; usually empty on LinkedIn).")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y-%m-%dT%H-%M-%S")

    if args.use_cache and os.path.exists(CACHE_PATH):
        print(f"[cache] loading previous scrape from {CACHE_PATH}")
        raw = json.load(open(CACHE_PATH))
        jobs_raw = raw["jobs"]
    else:
        print(f"Scraping LinkedIn with {len(ROLE_QUERIES)} role queries @ {LOCATION} ...")
        li = LinkedInGuestScraper()
        jobs_raw = []
        for q in ROLE_QUERIES:
            js = asyncio.run(li.search(queries=[q], location=LOCATION, max_pages_per_query=1))
            jobs_raw.extend([asdict_safe(j) for j in js])
        json.dump({"jobs": jobs_raw,
                   "scraped_at": ts.isoformat()},
                  open(CACHE_PATH, "w"), indent=2, ensure_ascii=False)

    jobs = [JobPosting(**j) if isinstance(j, dict) else j for j in jobs_raw]

    # Dedup within run: by URL, then by normalised (title+company).
    seen_url, seen_key, all_jobs = set(), set(), []
    for j in jobs:
        if j.url in seen_url:
            continue
        key = re.sub(r"\s+", " ", f"{j.title}||{j.company}".lower()).strip()
        if key in seen_key:
            continue
        seen_url.add(j.url)
        seen_key.add(key)
        all_jobs.append(j)

    # Relevance gate (resume-matched)
    relevant = [j for j in all_jobs if is_relevant(j)]

    # Cross-run dedup: exclude anything already delivered in a prior run.
    hist = load_history()
    if not hist:
        seeded = seed_history_from_reports(hist)
        if seeded:
            print(f"Seeded history from prior reports: {seeded} jobs marked as already-seen")
    fresh = [j for j in relevant if job_key(j) not in hist]
    print(f"Total deduped: {len(all_jobs)} | Resume-relevant: {len(relevant)} | "
          f"Already-seen: {len(relevant) - len(fresh)} | FRESH: {len(fresh)}")

    for j in fresh:
        j._score = score(j)            # type: ignore[attr-defined]
        j._guj = loc_tier(j) == 10     # type: ignore[attr-defined]

    fresh.sort(key=lambda x: (-x._score, not x._guj))  # type: ignore[attr-defined]
    guj = [j for j in fresh if j._guj]                 # type: ignore[attr-defined]
    top = fresh[:50]
    print(f"Top 50 (capped): {len(top)} | Gujarat-priority in top: {len(guj)}")

    # Optional: best-effort apply-email harvest
    if args.fetch_emails:
        print("Harvesting apply-emails (best-effort) ...")
        for j in top:
            j._email = asyncio.run(fetch_apply_email(j.url))  # type: ignore[attr-defined]
    else:
        for j in top:
            j._email = ""  # type: ignore[attr-defined]

    # Persist newly-seen jobs to history (only on a real run — dry-run must
    # not consume the fresh set).
    new_recs = [{"key": job_key(j), "title": j.title, "company": j.company,
                 "url": j.url, "first_seen": stamp} for j in top]
    if not args.dry_run:
        append_history(new_recs)

    now = ts.strftime("%Y-%m-%d %H:%M UTC")
    md_path = os.path.join(ART, f"job_report_{stamp}_scrapling.md")
    lines = [
        "# CareerPilot — Fresh Jobs Report (resume-matched, new since last run)",
        "",
        f"*Generated: {now}*",
        f"*Method:* LinkedIn guest search, {len(ROLE_QUERIES)} resume-targeted role queries @ {LOCATION}. Already-delivered jobs excluded.",
        f"*Resume-relevant scraped:* {len(relevant)}  |  *Fresh (new):* {len(fresh)}  |  *Gujarat-priority in fresh:* {len(guj)}",
        "",
        "| # | Score | Role | Company | Location | Apply (LinkedIn) | Apply Email |",
        "|---|------:|------|---------|----------|-----------------|-------------|",
    ]
    for i, j in enumerate(top, 1):
        tag = " 🟢GUJ" if j._guj else ""                       # type: ignore[attr-defined]
        url = j.url or ""
        url_md = f"[link]({url})" if url else "-"
        email = j._email or "—"                                # type: ignore[attr-defined]
        lines.append(f"| {i} | {j._score} | {md_escape(j.title)}{tag} | {md_escape(j.company)} | "  # type: ignore[attr-defined]
                     f"{md_escape(j.location)} | {url_md} | {md_escape(email)} |")
    lines.append("")
    lines.append("> Apply via the LinkedIn link (Easy Apply / external ATS). "
                 "LinkedIn's free guest data exposes no recruiter email, so the Apply Email column is usually empty — use `--fetch-emails` to attempt a harvest per job.")
    report = "\n".join(lines) + "\n"

    with open(md_path, "w") as f:
        f.write(report)
    top_json = [{"title": j.title, "company": j.company, "location": j.location,
                 "source": j.source, "url": j.url, "score": j._score,   # type: ignore[attr-defined]
                 "gujarat": j._guj, "email": j._email} for j in top]   # type: ignore[attr-defined]
    with open(os.path.join(ART, f"top50_{stamp}_scrapling.json"), "w") as f:
        json.dump(top_json, f, indent=2, ensure_ascii=False)
    with open(os.path.join(ART, "top50_scrapling.json"), "w") as f:  # latest snapshot
        json.dump(top_json, f, indent=2, ensure_ascii=False)

    # Telegram text (top 15)
    txt = [f"📋 *CareerPilot — fresh resume-matched jobs* ({now})",
           f"Fresh: *{len(fresh)}* (excludes {len(relevant) - len(fresh)} already-sent) | Gujarat: *{len(guj)}*",
           "*Top matches:*"]
    for i, j in enumerate(top[:15], 1):
        tag = " 🟢" if j._guj else ""                              # type: ignore[attr-defined]
        txt.append(f"{i}. {j.title}{tag} — {j.company} ({j.location})")
    txt.append("Apply links in the attached report ↓")

    if args.dry_run:
        print("\n[DRY RUN] Would send:\n" + "\n".join(txt))
        print(f"\n[DRY RUN] Report written to {md_path} (not sent)")
        return

    send_to_telegram("\n".join(txt), md_path)
    print(f"Report -> {md_path}")


def asdict_safe(j: JobPosting) -> dict:
    return {
        "source": j.source, "source_job_id": j.source_job_id, "title": j.title,
        "company": j.company, "location": j.location, "description": j.description,
        "url": j.url, "posted_at": j.posted_at, "salary": j.salary,
        "employment_type": j.employment_type, "work_mode": j.work_mode,
        "skills": j.skills, "experience_required": j.experience_required,
        "hash_key": j.hash_key, "scraped_at": j.scraped_at,
    }


if __name__ == "__main__":
    main()
