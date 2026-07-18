#!/usr/bin/env python3
"""Sokrates filter – odfiltrowuje nowe wzmianki @sokrates i formatuje powiadomienie.
Pomija komentarze oznaczone jako 'Zrobione przez Sokratesa'.
Dodatkowo zapisuje znalezione zadania do pliku dla Job 2.

Usage: sokrates-filter.py <issues.json> <comments.json> <repo_name>
"""
import json, sys, os

if len(sys.argv) != 4:
    sys.exit(0)

issues_path = sys.argv[1]
comments_path = sys.argv[2]
REPO = sys.argv[3]

with open(issues_path) as f:
    issues_raw = json.load(f)
with open(comments_path) as f:
    comments_raw = json.load(f)

DONE_MARKER = "Zrobione przez Sokratesa"
TASK_FILE = os.path.expanduser("~/.hermes/scripts/.sokrates-tasks.json")

# --- filtruj issue ---
new_issues = []
for i in issues_raw:
    if "pull_request" in i:
        continue
    title = (i.get("title") or "").lower()
    body = (i.get("body") or "").lower()
    if "@sokrates" in title or "@sokrates" in body:
        if DONE_MARKER.lower() in title or DONE_MARKER.lower() in body:
            continue
        new_issues.append(i)

# --- filtruj komentarze ---
new_comments = []
for c in comments_raw:
    body = c.get("body") or ""
    if DONE_MARKER.lower() in body.lower():
        continue
    if "@sokrates" in body.lower():
        new_comments.append(c)

# --- Zapisz zadania do pliku dla Job 2 ---
tasks = []
existing_tasks = []
if os.path.exists(TASK_FILE):
    try:
        with open(TASK_FILE) as f:
            existing_tasks = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

for i in new_issues:
    body = (i.get("body") or "")[:500]
    tasks.append({
        "type": "issue",
        "repo": REPO,
        "number": i["number"],
        "title": i["title"],
        "body": body,
        "url": i["html_url"],
        "user": i["user"]["login"]
    })
for c in new_comments:
    body = c.get("body") or ""
    tasks.append({
        "type": "comment",
        "repo": REPO,
        "comment_id": c["id"],
        "body": body,
        "url": c["html_url"],
        "user": c["user"]["login"],
        "issue_url": c["issue_url"]
    })

if tasks:
    # Dodaj do istniejących zadań (unikaj duplikatów po comment_id / issue number+repo)
    existing_ids = set()
    for t in existing_tasks:
        if t.get("type") == "comment":
            existing_ids.add(("comment", t["repo"], t["comment_id"]))
        elif t.get("type") == "issue":
            existing_ids.add(("issue", t["repo"], t["number"]))
    
    for t in tasks:
        if t["type"] == "comment":
            key = ("comment", t["repo"], t["comment_id"])
        else:
            key = ("issue", t["repo"], t["number"])
        if key not in existing_ids:
            existing_tasks.append(t)
    
    with open(TASK_FILE, "w") as f:
        json.dump(existing_tasks, f, ensure_ascii=False)

# --- Powiadomienie dla usera (stdout) ---
if not new_issues and not new_comments:
    sys.exit(0)  # exit 0 = cisza dla tego repo

print(f"🦉 **Sokrates melduje aktywność w {REPO}**")
print()

if new_issues:
    print("*Nowe issue ze wzmianką @sokrates:*")
    for i in new_issues:
        body = (i.get("body") or "")[:500].replace("\n", " ")
        suffix = "..." if len(i.get("body") or "") > 500 else ""
        repo_url = f"https://github.com/{REPO}"
        print(f'  • [#{i["number"]} {i["title"]}]({i["html_url"]})')
        print(f'    _{body}{suffix}_')
        print()

if new_comments:
    by_issue = {}
    for c in new_comments:
        issue_num = c["issue_url"].split("/")[-1]
        by_issue.setdefault(issue_num, []).append(c)

    print("*Nowe komentarze ze wzmianką @sokrates:*")
    for issue_num, items in sorted(by_issue.items()):
        issue_url = f"https://github.com/{REPO}/issues/{issue_num}"
        print(f'  **Issue [#{issue_num}]({issue_url})** — {len(items)} nowych komentarzy:')
        for c in items:
            body = (c.get("body") or "")[:500]
            suffix = "..." if len(c.get("body") or "") > 500 else ""
            print(f'    ┌─ @{c["user"]["login"]} (id: {c["id"]}):')
            for line in body.split("\n"):
                print(f'    │ {line}')
            if suffix:
                print(f'    │ {suffix}')
            print(f'    └─ {c["html_url"]}')
            print()

print("–––")
print("Czy chcesz, żebym zajął się którymś z tych zadań?")
print()
print("⚡ *Job 2 (Sokrates Executor) też to sprawdzi – możesz po prostu czekać.*")