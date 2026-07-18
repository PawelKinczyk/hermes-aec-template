---
name: toggl-track
description: "Toggl Track time tracking via API v9 — start/stop timer, list projects, today's entries, weekly report."
version: 1.0.0
author: hermes
license: MIT
platforms: [linux, macos]
prerequisites:
  env_vars: [TOGGL_API_TOKEN]
metadata:
  hermes:
    tags: [Toggl, Time Tracking, Productivity, API]
---

# Toggl Track

Toggl Track API v9 integration. Uses Basic Auth with API token as password.

## Setup

1. Get API token from Toggl Track: Profile → API Token
2. Add to `~/.hermes/.env`:
   ```
   TOGGL_API_TOKEN=***
   ```

## API Basics

- Base URL: `https://api.track.toggl.com/api/v9`
- Auth: Basic (`-u "${TOGGL_API_TOKEN}:api_token"`)
- Content-Type: `application/json`
- Workspace ID: `\$TOGGL_WORKSPACE_ID` (default)

## Common Commands

### Start timer (running, now)
```bash
source ~/.hermes/.env
curl -s -u "${TOGGL_API_TOKEN}:api_token" \
  -H "Content-Type: application/json" \
  -X POST "https://api.track.toggl.com/api/v9/workspaces/\$TOGGL_WORKSPACE_ID/time_entries" \
  -d '{"description":"opis zadania","project_id":INT,"created_with":"hermes","workspace_id":\$TOGGL_WORKSPACE_ID}'
```

### Create backdated entry (start + stop)
```bash
source ~/.hermes/.env
curl -s -u "${TOGGL_API_TOKEN}:api_token" \
  -H "Content-Type: application/json" \
  -X POST "https://api.track.toggl.com/api/v9/workspaces/\$TOGGL_WORKSPACE_ID/time_entries" \
  -d '{"description":"opis zadania","project_id":INT,"start":"2026-07-14T08:00:00.000+02:00","stop":"2026-07-14T11:00:00.000+02:00","created_with":"hermes","workspace_id":\$TOGGL_WORKSPACE_ID}'
```

### Stop current timer
```bash
source ~/.hermes/.env
curl -s -u "${TOGGL_API_TOKEN}:api_token" \
  -X PATCH "https://api.track.toggl.com/api/v9/workspaces/\$TOGGL_WORKSPACE_ID/time_entries/{time_entry_id}/stop"
```

### Get current running timer
```bash
source ~/.hermes/.env
curl -s -u "${TOGGL_API_TOKEN}:api_token" \
  "https://api.track.toggl.com/api/v9/me/time_entries/current"
```

### Today's time entries
```bash
source ~/.hermes/.env
curl -s -u "${TOGGL_API_TOKEN}:api_token" \
  "https://api.track.toggl.com/api/v9/me/time_entries"
```

### List projects
```bash
source ~/.hermes/.env
curl -s -u "${TOGGL_API_TOKEN}:api_token" \
  "https://api.track.toggl.com/api/v9/workspaces/\$TOGGL_WORKSPACE_ID/projects"
```

### Get user info
```bash
source ~/.hermes/.env
curl -s -u "${TOGGL_API_TOKEN}:api_token" \
  "https://api.track.toggl.com/api/v9/me"
```

## Known Projects (ID mapping)

| Project | ID |
|---|---|
| 240 CKD | 186473717 |
| 3LM | 219140815 |
| 418 ADA | 190732338 |
| 421 RADIO | 188402257 |
| 480 | 212672148 |
| 4LM | 219140811 |
| 529 | 212626985 |
| ANALIZA RYNKU | 176068311 |
| Anin | 197438564 |
| B&P | 220641884 |
| BLOG | 176384476 |
| Industria | 200332366 |
| Inne | 190732390 |
| M | 178041663 |
| MGR IiE | 176446216 |
| Ogólne | 219140816 |
| P&W | 186490959 |
| PLISZKA | 181747949 |
| PROGRAMOWANIE/DYNAMO | 178209787 |
| Scanplan | 194147806 |
| Ursus | 220611958 |
| WWA Wsch-zach | 220378337 |

## Notes

- Rate limit: ~500 req/min
- Use `created_with: "hermes"` for tracking source
- To get the current running time entry ID: call `GET /me/time_entries/current` and extract the `id` field
- Today's entries can be filtered by date range
- Workspace ID is stable (\$TOGGL_WORKSPACE_ID)