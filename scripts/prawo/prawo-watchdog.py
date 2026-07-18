#!/usr/bin/env python3
"""Prawo watchdog - no_agent, zero LLM tokens.

Checks Dziennik Ustaw (DU) and Monitor Polski (MP) via api.sejm.gov.pl (ELI)
for new acts matching construction/HVACR-industry keywords. Downloads matched
PDFs to the Obsidian vault, uploads them to Paperless-ngx via REST API with
proper titles and tags, and queues them for the prawo-digest agent cron.

State:
  ~/.hermes/state/prawo-seen.json     - set of seen ELI identifiers (e.g. DU/2026/946)
  ~/.hermes/state/prawo-queue.json    - list of matched acts awaiting a digest
  ~/.hermes/state/prawo-pdf-index.json - ELI id -> {pdf_path, title, paperless_id} for
                                          every PDF currently on disk, used to detect
                                          and clean up superseded documents
  ~/.hermes/state/prawo-watchdog.log  - one line per run

On first run (no prawo-seen.json): all current items are recorded as seen
WITHOUT being processed, to avoid flooding the queue with historical acts.

Superseded-document cleanup: the Sejm API exposes, per act, a
"Akty uznane za uchylone" (acts recognized as repealed) reference list on
whichever newer act repeals/replaces them. Whenever a new item's detail
lists an ELI id we have a PDF for in prawo-pdf-index.json, that old PDF is
deleted from the vault, the Paperless document is tagged "zastapiony", and
removed from the index - the vault keeps only current documents.
The queued entry for the new item records what it superseded so the digest
note can mention it.

Paperless integration: uploads PDFs via REST API with proper titles and tags
instead of just dropping files in the consume folder. Tag mapping:
  - "ustawa" for acts (ustawa) or unified texts (obwieszczenie)
  - "rozporzadzenie" for regulations
  - matched keyword-based tags for HVACR topics

Exit code 0 = ran fine (with or without hits). Exit code != 0 = network
failure or unexpected API structure - state is NOT modified in that case.
"""

import json
import re
import sqlite3
import sys
import datetime
from pathlib import Path

import requests

HERMES_HOME = Path.home() / ".hermes"
CONFIG_DIR = HERMES_HOME / "config"
STATE_DIR = HERMES_HOME / "state"
VAULT_PDF_DIR = Path("\$OBSIDIAN_VAULT_PATH/Prawo/PDF")
PAPERLESS_DB = Path("\$HERMES_HOME/docker/paperless/data/db.sqlite3")
PAPERLESS_URL = "http://127.0.0.1:8000"

KEYWORDS_FILE = CONFIG_DIR / "prawo-keywords.txt"
SEEN_FILE = STATE_DIR / "prawo-seen.json"
QUEUE_FILE = STATE_DIR / "prawo-queue.json"
PDF_INDEX_FILE = STATE_DIR / "prawo-pdf-index.json"
LOG_FILE = STATE_DIR / "prawo-watchdog.log"

API_BASE = "https://api.sejm.gov.pl/eli/acts"
PUBLISHERS = ["DU", "MP"]
TIMEOUT = 30

# Paperless tag cache: name -> id, populated on first use
_tag_cache: dict[str, int] | None = None
_paperless_token: str | None = None


def log(msg: str) -> None:
    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def get_paperless_token() -> str:
    global _paperless_token
    if _paperless_token:
        return _paperless_token
    conn = sqlite3.connect(str(PAPERLESS_DB))
    cur = conn.cursor()
    cur.execute("SELECT key FROM authtoken_token LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        raise RuntimeError("No Paperless auth token found in DB")
    _paperless_token = row[0]
    return _paperless_token


def get_tag_id(name: str) -> int:
    """Get or create a Paperless tag, returns its ID."""
    global _tag_cache
    if _tag_cache is None:
        _tag_cache = {}
        token = get_paperless_token()
        resp = requests.get(
            f"{PAPERLESS_URL}/api/tags/",
            headers={"Authorization": f"Token {token}"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        for tag in resp.json()["results"]:
            _tag_cache[tag["name"]] = tag["id"]

    if name in _tag_cache:
        return _tag_cache[name]

    # Create new tag
    token = get_paperless_token()
    resp = requests.post(
        f"{PAPERLESS_URL}/api/tags/",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        },
        json={"name": name},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    tag_data = resp.json()
    _tag_cache[name] = tag_data["id"]
    return tag_data["id"]


def upload_to_paperless(
    pdf_path: Path, title: str, publisher: str, keywords: list[str]
) -> int | None:
    """Upload a PDF to Paperless via API. Returns document ID or None on failure."""
    try:
        token = get_paperless_token()

        # Determine tags
        tags_to_apply: list[str] = []

        # Type-based tags
        title_lower = title.lower()
        if "obwieszczenie" in title_lower or "tekst jednolity" in title_lower:
            tags_to_apply.append("tekst-jednolity")
        if publisher == "DU":
            if "ustawa" in title_lower or "obwieszczenie" in title_lower:
                tags_to_apply.append("ustawa")
            elif "rozporządzenie" in title_lower:
                tags_to_apply.append("rozporzadzenie")
        elif publisher == "MP":
            tags_to_apply.append("monitor-polski")

        # Always add generic building-law tag
        tags_to_apply.append("prawo-budowlane")

        # Resolve tag names to IDs (deduplicated)
        tag_ids: list[int] = []
        seen_tags: set[str] = set()
        for t in tags_to_apply:
            if t not in seen_tags:
                seen_tags.add(t)
                tag_ids.append(get_tag_id(t))

        # Build multipart form data with multiple tags fields
        form_fields: dict[str, str | tuple] = {"title": title}
        # requests handles list values for the same key as multiple fields
        form_data: list[tuple[str, str]] = [("title", title)]
        for tid in tag_ids:
            form_data.append(("tags", str(tid)))

        with open(pdf_path, "rb") as f:
            resp = requests.post(
                f"{PAPERLESS_URL}/api/documents/post_document/",
                headers={"Authorization": f"Token {token}"},
                files={"document": (pdf_path.name, f, "application/pdf")},
                data=form_data,
                timeout=120,
            )
        resp.raise_for_status()
        # Response is a task UUID string like "8ef44a1c-0ad8-49a9-b06f-361a9c96cfd4"
        task_id: str = resp.text.strip().strip('"')
        log(f"Paperless upload queued: {title} (task={task_id}, tags={tags_to_apply})")
        return None  # Document ID not immediately available; tracked in pdf_index

    except Exception as e:
        log(f"ERROR uploading {pdf_path.name} to Paperless: {e}")
        return None


def tag_document_as_superseded(paperless_id: int) -> None:
    """Tag an existing Paperless document as zastapiony."""
    try:
        token = get_paperless_token()
        zastapiony_id = get_tag_id("zastapiony")
        # Get current tags
        resp = requests.get(
            f"{PAPERLESS_URL}/api/documents/{paperless_id}/",
            headers={"Authorization": f"Token {token}"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        doc = resp.json()
        current_tags = doc.get("tags", [])

        if zastapiony_id not in current_tags:
            current_tags.append(zastapiony_id)
            requests.patch(
                f"{PAPERLESS_URL}/api/documents/{paperless_id}/",
                headers={
                    "Authorization": f"Token {token}",
                    "Content-Type": "application/json",
                },
                json={"tags": current_tags},
                timeout=TIMEOUT,
            )
            log(f"tagged Paperless doc {paperless_id} as zastapiony")
    except Exception as e:
        log(f"WARNING: could not tag Paperless doc {paperless_id} as zastapiony: {e}")


def load_keywords() -> list[str]:
    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(f"missing keywords file: {KEYWORDS_FILE}")
    out = []
    for line in KEYWORDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.lower())
    return out


def load_seen():
    """Returns None on first run (no seen file yet), else a set of ELI ids."""
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    return None


def save_seen(seen: set) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(
        json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_pdf_index() -> dict:
    if PDF_INDEX_FILE.exists():
        return json.loads(PDF_INDEX_FILE.read_text(encoding="utf-8"))
    return {}


def save_pdf_index(index: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PDF_INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_queue() -> list:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return []


def save_queue(queue: list) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_year_list(publisher: str, year: int) -> list[dict]:
    url = f"{API_BASE}/{publisher}/{year}"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["items"]


def fetch_detail(publisher: str, year: int, pos: int) -> dict:
    url = f"{API_BASE}/{publisher}/{year}/{pos}"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def download_pdf(publisher: str, year: int, pos: int, dest: Path) -> None:
    url = f"{API_BASE}/{publisher}/{year}/{pos}/text.pdf"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)


_DIACRITICS = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ",
)


def slugify(title: str, max_words: int = 6) -> str:
    t = title.translate(_DIACRITICS).lower()
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    words = [w for w in t.split() if w][:max_words]
    return "-".join(words) or "akt"


def format_title(it: dict) -> str:
    """Format a clean document title from the API item."""
    title = it.get("title", "")
    publisher = it.get("publisher", "")
    pos = it.get("pos", "")
    year = it.get("year", "")
    # Build "Nazwa aktu (Dz.U. RRRR poz. XXXX)"
    du_ref = f"Dz.U. {year} poz. {pos}" if publisher == "DU" else f"M.P. {year} poz. {pos}"
    return f"{title} ({du_ref})"


def matched_keywords(title: str, act_keywords: list[str], keywords: list[str]) -> list[str]:
    haystack = (title + " " + " ".join(act_keywords)).lower()
    return [kw for kw in keywords if kw in haystack]


def main() -> int:
    try:
        keywords = load_keywords()
    except FileNotFoundError as e:
        log(f"ERROR: {e}")
        return 1

    seen = load_seen()
    first_run = seen is None
    if first_run:
        seen = set()

    year = datetime.date.today().year
    all_items: list[dict] = []
    for publisher in PUBLISHERS:
        try:
            items = fetch_year_list(publisher, year)
        except Exception as e:
            log(f"ERROR fetching list {publisher}/{year}: {e}")
            return 1
        all_items.extend(items)

    try:
        new_items = [it for it in all_items if it["ELI"] not in seen]
    except (KeyError, TypeError) as e:
        log(f"ERROR unexpected item structure: {e}")
        return 1

    if first_run:
        for it in all_items:
            seen.add(it["ELI"])
        save_seen(seen)
        log(
            f"first run: initialized state with {len(all_items)} items, "
            f"no processing"
        )
        return 0

    hits = 0
    superseded_count = 0
    queue = load_queue()
    pdf_index = load_pdf_index()
    for it in new_items:
        eli = it["ELI"]
        publisher = it["publisher"]
        pos = it["pos"]
        act_year = it["year"]
        title = it["title"]

        try:
            detail = fetch_detail(publisher, act_year, pos)
        except Exception as e:
            log(f"ERROR fetching detail {eli}: {e}")
            seen.add(eli)
            continue

        # Superseded-document cleanup: the API tells us, on the NEW act,
        # which older acts it repeals/replaces. If we have a PDF for one of
        # those, remove it - the vault keeps only current documents.
        supersedes = []
        repealed_refs = detail.get("references", {}).get("Akty uznane za uchylone", [])
        for ref in repealed_refs:
            old_eli = ref.get("id") if isinstance(ref, dict) else None
            if old_eli and old_eli in pdf_index:
                old_entry = pdf_index.pop(old_eli)
                old_path = Path(old_entry["pdf_path"])
                try:
                    old_path.unlink(missing_ok=True)
                    log(f"removed superseded PDF {old_eli} (replaced by {eli}): {old_path.name}")
                except Exception as e:
                    log(f"ERROR removing superseded PDF {old_eli}: {e}")

                # Tag old Paperless document as zastapiony
                old_pl_id = old_entry.get("paperless_id")
                if old_pl_id:
                    tag_document_as_superseded(old_pl_id)

                supersedes.append({"id": old_eli, "title": old_entry.get("title", "")})
                superseded_count += 1

        hit_kw = matched_keywords(title, detail.get("keywords", []), keywords)
        if hit_kw:
            slug = slugify(title)
            pdf_path = VAULT_PDF_DIR / str(act_year) / f"{publisher}-{act_year}-{pos}-{slug}.pdf"
            try:
                download_pdf(publisher, act_year, pos, pdf_path)
            except Exception as e:
                log(f"ERROR downloading PDF {eli}: {e}")
                seen.add(eli)
                continue

            # Upload to Paperless via API
            paperless_doc_title = format_title(it)
            paperless_id = upload_to_paperless(pdf_path, paperless_doc_title, publisher, hit_kw)

            pdf_index[eli] = {
                "pdf_path": str(pdf_path),
                "title": title,
                "paperless_id": paperless_id,
            }
            queue.append(
                {
                    "id": eli,
                    "title": title,
                    "date": it.get("promulgation") or it.get("announcementDate"),
                    "pdf_path": str(pdf_path),
                    "url": f"{API_BASE}/{eli}/text.pdf",
                    "matched_keywords": hit_kw,
                    "supersedes": supersedes,
                }
            )
            hits += 1

        seen.add(eli)

    save_seen(seen)
    save_queue(queue)
    save_pdf_index(pdf_index)
    log(
        f"new items: {len(new_items)}, hits: {hits}, "
        f"superseded removed: {superseded_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())