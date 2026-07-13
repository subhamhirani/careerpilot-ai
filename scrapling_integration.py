#!/usr/bin/env python3
"""
CareerPilot -> Scrapling integration.

Reuses the *techniques* already defined in
backend/app/agents/multi_portal_scraper.py (LinkedIn guest API, Naukri public
API, keyless APIs, rate-limiting, normalised JobPosting) but:

  1. DRIVES THEM WITH THE ROLE-TARGETED QUERY LIST instead of the
     scrape_all() default of ["software engineer"]. (The scraper's own
     DEFAULT_QUERIES for network/infra/sysadmin were never reached because
     scrape_all overrides queries with a non-None list. Passing the real
     role queries is what makes the scrape *relevant*.)
  2. Biases location to "Ahmedabad, Gujarat" so LinkedIn/Naukri return
     more local roles.
  3. Adds Gujarat post-fetch filtering + resume scoring.
  4. Uses Scrapling's Fetcher as a supplementary channel (best-effort).
  5. Delivers the ranked report to the LIVE Telegram gateway (reads .env).

Run:
  /home/ubuntu/scrapling-venv/bin/python /home/ubuntu/careerpilot/scrapling_integration.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone

sys.path.insert(0, "/home/ubuntu/careerpilot/backend/app/agents")
from multi_portal_scraper import scrape_all, JobPosting  # noqa: E402

import httpx  # noqa: E402

ROOT = "/home/ubuntu/careerpilot"
ENV_PATH = os.path.join(ROOT, ".env")
ART = os.path.join(ROOT, "artifacts")
os.makedirs(ART, exist_ok=True)

# ---- Role-targeted queries (the "techniques" that were being bypassed) ----
ROLE_QUERIES = [
    "network engineer", "infrastructure engineer", "system administrator",
    "windows administrator", "linux administrator", "devops engineer",
    "support engineer", "it support", "security analyst", "soc analyst",
    "cloud engineer", "network administrator", "technical support",
    "system engineer", "helpdesk", "cyber security",
]
LOCATION = "Ahmedabad, Gujarat"

# ---- Resume scoring (reused from report builder) ----
TITLE_W = {
    r"network\s*eng|network\s*admin|network\s*ops": 26,
    r"infrastructure": 22,
    r"system\s*admin|sysadmin|windows\s*admin|linux\s*admin|server\s*admin": 22,
    r"security\s*analyst|soc\s*analyst|siem": 21,
    r"support\s*eng|support\s*tech|it\s*support|helpdesk|desktop\s*support|technical\s*support": 18,
    r"devops|cloud\s*eng|cloud\s*infra": 17,
    r"system\s*engineer": 16,
}
DESC_SKILLS = ["windows server","active directory","ad ds","group policy","gpo","dns","dhcp","rras",
    "hyper-v","iis","docker","kubernetes","aws","ec2","vpc","iam","s3","linux","ubuntu","centos",
    "rhel","vlan","ospf","routing","switching","subnet","vpn","firewall","siem","wazuh","soc",
    "backup","disaster recovery","dr","network","tcp/ip","wireshark","ci/cd","terraform","ansible",
    "nginx","monitoring","grafana","prometheus","ssh","bash","powershell"]
GUJ_CITIES = ["ahmedabad","gandhinagar","gift city","vadodara","baroda","surat","rajkot","gujarat"]


def is_gujarat(j: JobPosting) -> bool:
    blob = f"{j.location} {j.title} {j.description}".lower()
    return any(c in blob for c in GUJ_CITIES)


def score(j: JobPosting) -> int:
    t = j.title or ""
    s = 0
    for rx, w in TITLE_W.items():
        if re.search(rx, t, re.I):
            s += w
    blob = " ".join([j.description or "", " ".join(j.skills or []), t, j.company or ""]).lower()
    s += min(30, sum(1 for k in DESC_SKILLS if k in blob) * 2)
    s += 15 if is_gujarat(j) else (5 if "india" in (j.location or "").lower() else 3)
    return s


# ---- Scrapling Fetcher (supplementary, best-effort) ----
async def scrapling_supplement() -> list[JobPosting]:
    """Use Scrapling's Fetcher as an extra channel for the Naukri public API,
    which times out on a raw httpx call from this box but may succeed via
    Scrapling's transport. Guarded: never blocks delivery."""
    try:
        from scrapling.fetchers import Fetcher
    except Exception:
        return []
    jobs: list[JobPosting] = []
    url = ("https://www.naukri.com/jobapi/v1/search?query="
           "network%20engineer&location=Ahmedabad&pageNo=1&pageSize=20")
    try:
        page = Fetcher.get(url, timeout=25, stealthy_headers=True)
        data = page.json()
        for item in data.get("list", [])[:20]:
            title = re.sub(r"<[^>]+>", "", item.get("post", "") or "").strip()
            if not title:
                continue
            loc = (item.get("cityfield") or "").strip()
            if not any(c in loc.lower() for c in GUJ_CITIES):
                continue
            jobs.append(JobPosting(
                source="naukri(scrapling)",
                source_job_id=str(item.get("jobId", ""))[:12] or "x",
                title=title, company=item.get("companyName", ""),
                location=loc, description="", url=item.get("urlStr", ""),
            ))
    except Exception as exc:
        print(f"[scrapling] supplement skipped: {exc}")
    return jobs


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
        r = client.post(f"{base}/sendMessage", json={"chat_id": chat, "text": text, "parse_mode": "Markdown"})
        print(f"Telegram sendMessage: ok={r.json().get('ok')} mid={r.json().get('result', {}).get('message_id')}")
        if not r.json().get("ok"):
            return False
        with open(doc_path, "rb") as d:
            r2 = client.post(f"{base}/sendDocument",
                             data={"chat_id": chat, "caption": "CareerPilot full report (ranked)"},
                             files={"document": ("report.md", d, "text/markdown")})
            print(f"Telegram sendDocument: ok={r2.json().get('ok')} mid={r2.json().get('result', {}).get('message_id')}")
        return r2.json().get("ok", False)


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").strip()


def main():
    print(f"Running scrape_all with {len(ROLE_QUERIES)} role queries @ {LOCATION} ...")
    result = asyncio.run(scrape_all(
        linkedin_queries=ROLE_QUERIES,
        naukri_queries=ROLE_QUERIES,
        location=LOCATION,
        use_local_fallback=True,
    ))
    jobs = [JobPosting(**j) if isinstance(j, dict) else j for j in result["jobs"]]

    # Scrapling supplementary channel
    supp = asyncio.run(scrapling_supplement())
    if supp:
        print(f"Scrapling supplement added {len(supp)} Gujarat Naukri jobs")
        jobs.extend(supp)

    # Dedup + score
    seen, scored = set(), []
    for j in jobs:
        h = j.hash_key
        if h in seen:
            continue
        seen.add(h)
        j._score = score(j)  # type: ignore[attr-defined]
        j._guj = is_gujarat(j)  # type: ignore[attr-defined]
        scored.append(j)

    scored.sort(key=lambda x: (-x._score, not x._guj))  # type: ignore[attr-defined]
    guj = [j for j in scored if j._guj]  # type: ignore[attr-defined]
    print(f"Total deduped: {len(scored)} | Gujarat-priority: {len(guj)}")

    # Top 50 report
    top = scored[:50]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# CareerPilot — Jobs Scrape Report (Scrapling integration)",
        "",
        f"*Generated: {now}*",
        f"*Method:* multi_portal_scraper techniques (LinkedIn guest + Naukri + keyless APIs) "
        f"driven with {len(ROLE_QUERIES)} role queries @ {LOCATION}; +Scrapling Fetcher supplement.",
        f"*Resume-targeted roles:* {len(scored)}  |  *Gujarat-priority:* {len(guj)}",
        "",
        "| # | Score | Role | Company | Location | Source | Apply |",
        "|---|------:|------|---------|----------|--------|-------|",
    ]
    for i, j in enumerate(top, 1):
        tag = " 🟢GUJ" if j._guj else ""  # type: ignore[attr-defined]
        url = j.url or ""
        url_md = f"[link]({url})" if url else "-"
        lines.append(f"| {i} | {j._score} | {md_escape(j.title)}{tag} | {md_escape(j.company)} | "  # type: ignore[attr-defined]
                     f"{md_escape(j.location)} | {j.source} | {url_md} |")
    report = "\n".join(lines) + "\n"

    md_path = os.path.join(ART, "job_report_2026-07-13_scrapling.md")
    with open(md_path, "w") as f:
        f.write(report)
    top_json = [{"title": j.title, "company": j.company, "location": j.location,
                 "source": j.source, "url": j.url, "score": j._score, "gujarat": j._guj}  # type: ignore[attr-defined]
                for j in top]
    with open(os.path.join(ART, "top50_scrapling.json"), "w") as f:
        json.dump(top_json, f, indent=2, ensure_ascii=False)

    # Telegram text (compact)
    txt = [f"📋 *CareerPilot scrape* ({now})",
           f"Resume-targeted: *{len(scored)}* | Gujarat: *{len(guj)}*",
           "*Top matches:*"]
    for i, j in enumerate(top[:15], 1):
        tag = " 🟢" if j._guj else ""  # type: ignore[attr-defined]
        txt.append(f"{i}. {j.title}{tag} — {j.company} ({j.location})")
    txt.append("Full report attached ↓")
    send_to_telegram("\n".join(txt), md_path)
    print(f"Report -> {md_path}")


if __name__ == "__main__":
    main()
