---
name: shopping
description: "Manage the shopping list at \$OBSIDIAN_VAULT_PATH/Zakupy/Lista.md from natural-language Telegram commands (add, show, remove, mark bought, clear). Hermes never invents or suggests items - only what the user explicitly dictates."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [Shopping, Telegram, Obsidian, Lists]
    related_skills: [knowledge]
---

# shopping — Zakupy/Lista.md management

## Golden rule (non-negotiable)

Hermes never invents, suggests, or auto-completes shopping items. It writes
to the list ONLY the exact items the user dictated in their message -
nothing more, nothing less. No "you probably also need X", no substituting
brand names, no splitting/merging items on your own judgment.

## File

`\$OBSIDIAN_VAULT_PATH/Zakupy/Lista.md` - written directly with
read_file/write_file/patch (same machine as the vault, do not use or debug
the Obsidian MCP server). Format:

```markdown
# Lista zakupów
Aktualizacja: YYYY-MM-DD HH:MM

- [ ] mleko 2%
- [ ] masło
- [ ] papier ścierny P120
```

If the file does not exist yet, create it with this header and an empty
item list. Always update the "Aktualizacja" timestamp on any write (get
the real date/time with the terminal `date` command, do not guess it).

## Commands (Polish natural-language triggers from Telegram)

| User says (example) | Action |
|---|---|
| "dodaj do zakupów: X, Y, Z" | Append each item as `- [ ] item`. Skip items that already exist in the list (case-insensitive match on the item text) and report which ones were skipped as duplicates. |
| "pokaż listę zakupów" | Reply with the current file content (or "lista jest pusta" if no items). |
| "usuń z zakupów: X" | Remove the matching line(s) (case-insensitive). Report if nothing matched. |
| "kupione: X, Y" | Check the matching item(s): `- [ ]` -> `- [x]`. Report if nothing matched. |
| "wyczyść kupione" | Remove all `- [x]` lines, keep `- [ ]` lines. |
| "wyczyść listę zakupów" | Ask for confirmation first ("na pewno wyczyścić całą listę?") before wiping everything - do not clear without an explicit yes in the reply that follows. |

## Reply style

Confirm what changed in 1-2 sentences (Polish, with proper diacritics, per SOUL.md) -
e.g. which items were added, which were skipped as duplicates, or the
current list content when asked to show it. Do not dump the raw markdown
file verbatim unless the user asked to see the list.
