---
name: knowledge
description: "Rules for saving knowledge to the Obsidian vault (\$OBSIDIAN_VAULT_PATH): content-to-folder mapping, YAML frontmatter templates with English attribute keys, naming convention, mandatory dedup search before creating notes, wikilinks to related notes."
version: 1.2.0
author: Hermes Agent
metadata:
  hermes:
    tags: [Obsidian, Vault, Notes, Knowledge, Frontmatter, Deduplication]
    related_skills: [obsidian, obsidian-note-pl]
---

# Knowledge — saving knowledge to the Obsidian vault

Vault: `\$OBSIDIAN_VAULT_PATH/` — the user's existing vault, synced
via paid Obsidian Sync. Hermes runs on the same machine as the vault, so
**write notes directly with read_file/write_file/patch/search_files** under
the vault path — this is the correct primary approach here, not a fallback.
The Obsidian MCP server (`obsidian`) is optional and may be unavailable
(server not installed, as of 2026-07-16); do not attempt to debug or retry
MCP connection failures, do not search .env/config for its credentials —
just use the file tools directly. Binary files (PDF) are always written
directly to disk regardless.

**Rebuilt vault (Mind 2.0):** the vault was replaced with Mind 2.0 content on
2026-07-17 (.obsidian/ config preserved from the original vault). All 315 .md
files have YAML frontmatter (date, time, tags, source, summary - English keys),
Polish content, and translated filenames. See `references/vault-rebuild.md` for
the rebuild procedure.

**Language rule: all note CONTENT is written in Polish. Frontmatter attribute
KEYS are in English (date, time, tags, source, status, summary). No emoji,
no decorative elements.**

## Vault vs. Paperless vs. RSS digest — three destinations, never overlapping

Three separate systems handle content today (Etap 4/7/8) — pick the right one
by asking what the content IS, not where it came from:

- **Vault (this skill)** — curated knowledge in your own words: summaries,
  dedup, wikilinks. The only raw files it holds are legal-act PDFs in
  `Prawo/PDF/` (linked from digest notes so the note has something to point at).
- **Paperless-ngx** (`~/paperless/consume`, query via `skill_view("paperless-ngx")`)
  — raw document archive with OCR + full-text search. For "find the exact
  document/phrase", never for summaries. Any PDF dropped into consume gets
  archived there automatically — no vault note is created unless separately
  asked for.
- **RSS digest** (FreshRSS -> `rss-watchdog`/`rss-digest`) — ephemeral by
  design: delivered once via Telegram, queue cleared after sending, nothing
  persisted anywhere. It only becomes a vault note if the user explicitly
  asks to save a specific link (`/doc-pipeline <url>`).

Only the legal-act pipeline (`prawo-watchdog.py`) dual-writes today: the PDF
goes to both `Prawo/PDF/` (vault) and Paperless consume, while the digest
note itself lives only in the vault. Don't assume other content types need
the same dual-write — it is specific to that one pipeline.

## Content-to-folder mapping

| Content | Folder |
|---|---|
| Web pages / articles | `Web/` |
| Law, legal acts, legal digests | `Prawo/` (PDFs go to `Prawo/PDF/`) |
| Shopping | `Zakupy/` (mainly `Zakupy/Lista.md`) |
| Project topics, repositories | `Projekty/` |
| Daily entries | `Daily/` (exists — do not change its format) |
| User's own knowledge notes | `Brain/` — NEVER auto-save there; it is the user's hand-written knowledge base (294+ notes). ALWAYS include it in dedup search and wikilink discovery. |

## Naming

`YYYY-MM-DD-short-slug.md` — slug without Polish diacritics, words separated
by hyphens, at most 4-5 words. Exceptions: `Zakupy/Lista.md` (fixed name),
`Daily/` (file name = date, no slug — existing convention).

## Rules for creating notes

1. Always use YAML frontmatter per the templates below. Note content in
   Polish. No emoji. No date header inside the body (the file name carries
   the date).
2. Prefer tables and checklists over long paragraphs.
3. **Dedup search (mandatory):** before creating a note, search the vault
   (MCP search) using 3-5 keywords from the title and tags — including the
   `Brain/` folder. If a note on the same topic exists — propose appending
   a section to it instead of creating a duplicate. For related-but-distinct
   hits — list them under "Powiazane notatki" as [[wikilinks]], each with a
   one-sentence justification (in Polish).
4. Hermes `memory`: only short facts and user preferences. Documents,
   summaries, longer content — always to the vault.
5. Never load whole vault folders into context — always specific notes
   (search first, then read the hits).

## Frontmatter attribute keys (English, required)

| Key | Value |
|---|---|
| `date` | YYYY-MM-DD (creation date) |
| `time` | HH:MM (creation time) |
| `tags` | list; lowercase, hyphenated; MUST use the key `tags` (Obsidian only indexes this key in its tag pane) |
| `source` | URL or origin of the content (where applicable) |
| `summary` | one sentence in Polish |
| `status` | `nowa` -> workflow states as needed |

## Template: Web note

```markdown
---
date: YYYY-MM-DD
time: HH:MM
tags: [web, <2-4 topical tags>]
source: <URL>
summary: <one sentence in Polish>
status: nowa
---
## Streszczenie
<5-10 zdan po polsku>

## Kluczowe fakty
- ...

## Powiazane notatki
- [[existing-note-name]] — jedno zdanie dlaczego powiazana
```

## Template: legal digest (`Prawo/YYYY-MM-DD-digest.md`)

```markdown
---
date: YYYY-MM-DD
time: HH:MM
tags: [prawo, budownictwo]
source: api.sejm.gov.pl (ELI)
summary: <one sentence in Polish>
---
## Nowe akty — YYYY-MM-DD
### <Tytul aktu>
- Identyfikator: DU/<rok>/<pozycja>
- PDF: [[Prawo/PDF/<plik>.pdf]]
- Streszczenie: <3-5 zdan>
- Dlaczego istotne: <1-2 zdania odniesienia do branzy>
- Link do oryginalu: <URL>
```
