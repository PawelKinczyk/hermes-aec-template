---
name: doc-pipeline
description: "Procedure for turning a URL into a vault note: fetch, classify folder, dedup/related-notes search, summarize, reply. Explicit-invocation only (user preference, 2026-07-16): run this ONLY when the user types /doc-pipeline <url> or explicitly asks to save/note down a link. Never auto-trigger just because a message contains a URL - e.g. 'summarize this article <url>' means summarize only, do not also save it unless asked."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [Web, Telegram, Notes, Obsidian, Summarization]
    related_skills: [knowledge]
---

# doc-pipeline — web link to vault note

**Explicit invocation only.** Run this procedure ONLY when the user types
the command `/doc-pipeline <url>`, or explicitly asks to save/note down a
link (e.g. "zapisz ten link", "dodaj to do notatek"). A bare link, or a
link with an unrelated instruction like "podsumuj ten artykul <url>", does
NOT trigger this skill - just do what was asked (e.g. summarize in chat)
and stop there. This is a deliberate user preference for predictability
over automatic behavior.

## Procedure

1. **Fetch.** Use `web_extract` (returns markdown). Only fall back to
   `browser` if `web_extract` returns empty or clearly truncated content -
   and only after telling the user on Telegram that the fast path failed
   and you are retrying with the browser (slower, costs more).

2. **Classify the folder.** Follow the content-to-folder mapping in
   `skill_view("knowledge")`: default `Web/`; legal content -> `Prawo/`;
   content about a repo/project -> `Projekty/`.

3. **Dedup / related-notes search (mandatory, do this BEFORE writing).**
   Search the vault directly on disk (`search_files`/`read_file` under
   `\$OBSIDIAN_VAULT_PATH/` - Hermes and the vault share the same
   machine, do not use or debug the Obsidian MCP server) using 3-5 keywords
   from the title and fetched content, including the `Brain/` folder:
   - same topic as an existing note -> do NOT create a new note; ask the
     user on Telegram whether to append a section to the existing note
     instead, and wait for their answer before writing anything.
   - related-but-distinct notes -> list them under "Powiazane notatki" as
     `[[wikilinks]]`, each with a one-sentence reason (in Polish).

4. **Write the note.** Use the Web template from `skill_view("knowledge")`
   (frontmatter with English keys: date, time, tags, source, summary).
   Summary: 5-10 sentences in Polish, in your own words - never paste large
   verbatim chunks of the source page. Add a short "Kluczowe fakty" list.

5. **Reply on Telegram (Polish, per SOUL.md - diacritics fine, no emoji/em-dash).** 2-3 sentences
   summarizing the content, the name of the note file created (or which
   note was appended to), and the related notes found (if any). Do not
   paste the full page content into the chat reply.

## Cost discipline

Everything on the default model (Flash) - this task does not warrant
delegation to Pro (see `skill_view("model-routing")`: this is a
summarization task, not multi-step analysis). For very long pages,
summarize section by section rather than dumping the whole page into one
prompt. Never paste the entire fetched page into the Telegram reply.
