#!/usr/bin/env python3
"""RSS watchdog - no_agent, zero LLM tokens.

Pulls unread items from a local FreshRSS instance (Google Reader / "GReader"
compatible API), matches title+summary against a keyword list, queues hits
for the digest agent cron, and marks every fetched item as read in FreshRSS
(hit or not) so the same item is never re-processed.

State:
  ~/.hermes/state/rss-queue.json    - list of matched articles awaiting a digest
  ~/.hermes/state/rss-watchdog.log  - one line per run

Credentials (never printed/logged): ~/.hermes/.env
  FRESHRSS_API_USER
  FRESHRSS_API_PASSWORD

Exit code 0 = ran fine (with or without hits). Exit code != 0 = login/network
failure or unexpected API structure - no items are marked as read in that
case, so nothing is lost.
"""

import html
import json
import os
import re
import sys
import datetime
from pathlib import Path

import requests

HERMES_HOME = Path.home() / ".hermes"
CONFIG_DIR = HERMES_HOME / "config"
STATE_DIR = HERMES_HOME / "state"

KEYWORDS_FILE = CONFIG_DIR / "rss-keywords.txt"
QUEUE_FILE = STATE_DIR / "rss-queue.json"
LOG_FILE = STATE_DIR / "rss-watchdog.log"
ENV_FILE = HERMES_HOME / ".env"

FRESHRSS_BASE = "http://\$FRESHRSS_HOST:8081/api/greader.php"
MAX_ITEMS = 200
TIMEOUT = 30


def log(msg: str) -> None:
    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def load_env_credentials() -> tuple[str, str]:
    user = pw = None
    if not ENV_FILE.exists():
        raise FileNotFoundError(f"missing env file: {ENV_FILE}")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("FRESHRSS_API_USER="):
            user = line.split("=", 1)[1].strip()
        elif line.startswith("FRESHRSS_API_PASSWORD="):
            pw = line.split("=", 1)[1].strip()
    if not user or not pw:
        raise ValueError("FRESHRSS_API_USER/FRESHRSS_API_PASSWORD not set in .env")
    return user, pw


def load_keywords() -> list[str]:
    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(f"missing keywords file: {KEYWORDS_FILE}")
    out = []
    for line in KEYWORDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.lower())
    return out


def load_queue() -> list:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return []


def save_queue(queue: list) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def login(user: str, password: str) -> str:
    resp = requests.post(
        f"{FRESHRSS_BASE}/accounts/ClientLogin",
        data={"Email": user, "Passwd": password},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    for line in resp.text.splitlines():
        if line.startswith("Auth="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ClientLogin response did not contain an Auth token")


def fetch_unread(auth: str) -> list[dict]:
    resp = requests.get(
        f"{FRESHRSS_BASE}/reader/api/0/stream/contents/reading-list",
        params={
            "xt": "user/-/state/com.google/read",
            "n": MAX_ITEMS,
            "output": "json",
        },
        headers={"Authorization": f"GoogleLogin auth={auth}"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def mark_read(auth: str, item_ids: list[str]) -> None:
    if not item_ids:
        return
    data = [("a", "user/-/state/com.google/read")]
    data.extend(("i", item_id) for item_id in item_ids)
    resp = requests.post(
        f"{FRESHRSS_BASE}/reader/api/0/edit-tag",
        data=data,
        headers={"Authorization": f"GoogleLogin auth={auth}"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub(" ", text or ""))


def matched_keywords(title: str, summary: str, keywords: list[str]) -> list[str]:
    haystack = (title + " " + strip_html(summary)).lower()
    return [kw for kw in keywords if kw in haystack]


def main() -> int:
    try:
        user, password = load_env_credentials()
        keywords = load_keywords()
    except (FileNotFoundError, ValueError) as e:
        log(f"ERROR: {e}")
        return 1

    try:
        auth = login(user, password)
    except Exception as e:
        log(f"ERROR logging into FreshRSS: {e}")
        return 1

    try:
        items = fetch_unread(auth)
    except Exception as e:
        log(f"ERROR fetching unread items: {e}")
        return 1

    queue = load_queue()
    hits = 0
    processed_ids = []

    for it in items:
        item_id = it.get("id")
        if not item_id:
            continue
        title = it.get("title", "")
        summary = (it.get("summary") or {}).get("content", "")
        origin = it.get("origin") or {}
        alt = (it.get("alternate") or [{}])[0]

        hit_kw = matched_keywords(title, summary, keywords)
        if hit_kw:
            queue.append(
                {
                    "title": title,
                    "url": alt.get("href", ""),
                    "source": origin.get("title", ""),
                    "published": it.get("published"),
                    "summary_html": summary,
                    "matched_keywords": hit_kw,
                }
            )
            hits += 1

        processed_ids.append(item_id)

    try:
        mark_read(auth, processed_ids)
    except Exception as e:
        log(f"ERROR marking items as read (queue NOT saved, will retry next run): {e}")
        return 1

    save_queue(queue)
    log(f"fetched: {len(items)}, hits: {hits}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
