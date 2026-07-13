#!/usr/bin/env python3
"""
Standalone Telegram sender for CareerPilot job reports.

WHY THIS FILE EXISTS
  The multi_portal_scraper.py does NOT send to Telegram. This is a
  separate, opt-in script you run yourself once you've set the two
  environment variables below. Nothing is sent unless both are present.

USAGE
  1. Export your credentials in the SHELL (never paste them in chat):
       export TELEGRAM_BOT_TOKEN="123456:ABC-your-token"
       export TELEGRAM_CHAT_ID="987654321"
  2. Run:
       /home/ubuntu/scrapling-venv/bin/python /home/ubuntu/careerpilot/telegram_sender.py

  To get a chat_id: message @userinfobot on Telegram, or print updates:
       curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates"

NOTE
  Telegram messages are capped at 4096 chars. The report is split into
  chunks automatically. Sent as plain text (no Markdown) to avoid
  escaping breakage.
"""
from __future__ import annotations
import os
import sys
import textwrap

import httpx

REPORT_PATH = "/home/ubuntu/careerpilot/artifacts/job_report_2026-07-13.md"
CHUNK = 3900  # safe margin under 4096


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set. Export it in your shell first.")
        return 2
    if not chat:
        print("ERROR: TELEGRAM_CHAT_ID not set. Export it in your shell first.")
        return 2

    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        print(f"ERROR: report not found at {REPORT_PATH}. Run the scraper first.")
        return 2

    chunks = textwrap.wrap(
        text, CHUNK, break_long_words=False, replace_whitespace=False
    ) or [text]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    sent = 0
    with httpx.Client(timeout=30.0) as client:
        for i, chunk in enumerate(chunks, 1):
            # Markdown header to delineate chunks
            body = f"[CareerPilot Report — part {i}/{len(chunks)}]\n\n{chunk}" if len(chunks) > 1 else chunk
            r = client.post(url, json={"chat_id": chat, "text": body})
            if r.status_code != 200:
                print(f"ERROR sending part {i}: HTTP {r.status_code} {r.text[:200]}")
                return 1
            sent += 1
            print(f"Sent part {i}/{len(chunks)} ({len(chunk)} chars)")

    print(f"Done. {sent} message(s) delivered to chat {chat}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
