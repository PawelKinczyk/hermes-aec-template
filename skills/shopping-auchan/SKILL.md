---
name: shopping-auchan
description: "Prepares an Auchan online shopping list (zakupy.auchan.pl) from the user's shopping list, one item per search. Adds matched products to the Auchan 'Typowa' list (NOT the cart) - the user finishes with a single native 'Dodaj wszystko' click and manual checkout. Use when the user explicitly asks to prepare/build an Auchan order from their list."
version: 1.1.0
author: Hermes Agent
metadata:
  hermes:
    tags: [Shopping, Auchan, Browser, Telegram]
    related_skills: [shopping]
---

# shopping-auchan — prepare an Auchan list from the shopping list

## Why this exists, and its hard boundary

Auchan's "Dodaj do koszyka" (add to cart) button is protected by AWS WAF Bot
Control - clicking it programmatically triggers a bot challenge instead of
adding the item (verified 2026-07-16). This is a deliberate anti-automation
measure. **Never attempt to click "Dodaj do koszyka" or otherwise add items
directly to the cart. Do not try to work around, defeat, or evade the WAF
challenge in any way.**

The separate "Dodaj do listy" (add to list) action is NOT behind this
protection (verified - it fires a normal GraphQL request, no WAF challenge).
This skill uses that instead: it builds up Auchan's own "Typowa" list. The
user then opens the Auchan site/app themselves and clicks the native
"Dodaj wszystko" (add all) button on that list - a single genuine human
click moves everything to the real cart. Checkout and payment are always
manual, exactly as originally intended.

## Step 1: Login (scripted, no LLM handles the password)

Run via terminal, once, at the start of the task:
```
\$HERMES_HOME/scripts/auchan-login.sh <session-name>
```
Pick a fresh `<session-name>` (e.g. `auchan_<random>`). Set a generous
timeout (90s+) -- the SSO redirect chain can take 30-60s.

Check the exit code:
- Exit 0: proceed to Step 2.
- Exit non-zero: STOP. Do not attempt the login yourself via
  browser_type with a real password. Report the exact error output to the
  user on Telegram and end the task. Known non-recoverable cases: wrong
  saved credentials (`agent-browser auth show auchan` to check the
  username only, never the password), Auchan changed their login page
  structure, or a network error.

### CRITICAL: agent-browser session vs Hermes browser tool

The login script creates a session in **agent-browser** (Chrome CDP via CLI).
The Hermes `browser_navigate/browser_click/browser_snapshot` tools use a
**separate, independent browser** (Browserbase/cua-driver). They do NOT
share sessions, cookies, or profile data. Reusing the `--session` flag
only works if you interact via terminal with `agent-browser` commands
directly:

```
\$HERMES_HOME/hermes-agent/node_modules/.bin/agent-browser --session <name> open <url>
\$HERMES_HOME/hermes-agent/node_modules/.bin/agent-browser --session <name> snapshot
\$HERMES_HOME/hermes-agent/node_modules/.bin/agent-browser --session <name> click @e3
```

**Do NOT mix tools** -- pick ONE browser driver for the whole task:
- Option A: use Hermes `browser_navigate/browser_click` tools (NO login
  session carried over from agent-browser -- user must be logged in
  already in that browser, or you must log in interactively).
- Option B: use `agent-browser` via terminal exclusively (session
  carries over from login, but must use terminal commands for every
  interaction, not Hermes browser tools).

This skill assumes Option B (agent-browser via terminal) because the
login is scripted. All "go to search", "click product", "snapshot", etc.
steps below must be executed via `agent-browser --session <name> <cmd>`,
NOT via Hermes browser tools.

### Login timeout handling

The login script has timed out (exit 124) after initial success when
Chrome processes from a prior run were left running. If the script times
out, run cleanup first:
```
pkill -f "agent-browser" 2>/dev/null; pkill -f "chrome" 2>/dev/null; sleep 2
```
Then retry with a fresh session name.

## Step 2: Read the shopping list

Read `\$OBSIDIAN_VAULT_PATH/Zakupy/Lista.md` (see skill
`shopping`), only the unchecked `- [ ]` items.

## Step 3: For each item, search and add to the list

All commands use `AB="\$HERMES_HOME/hermes-agent/node_modules/.bin/agent-browser"`.

1. Navigate to search:
   `$AB --session <name> open "https://zakupy.auchan.pl/search?q=<item text, url-encoded>"`
2. Snapshot: `$AB --session <name> snapshot -i`
3. If a cookie-consent, newsletter, or promo popup blocks the page (common
   on first load), close it via its visible close button ref before
   continuing - this is normal site behavior, not an error.
4. Look at the top few results. Pick the first sensible match for the
   item (same product family, no obviously wrong category). If the item
   text implies a quantity/size (e.g. "papryka pol kg"), prefer a result
   matching that size when available, but do not overthink it - "first
   sensible result" per the original rule.
5. If NO sensible result exists (nothing matches, or everything is a
   totally different product), or if there are multiple very different
   plausible matches with genuinely no way to prefer one (e.g. wildly
   different brands/sizes and nothing in the shopping list item
   disambiguates) - do NOT guess. Note the item under "do decyzji" for
   the final report and move to the next item.
6. Click into the chosen product (its heading or title link ref) to open
   the product detail page:
   `$AB --session <name> click @e<N>`
7. On the product detail page, look for a "Dodaj do listy" button. **The
   Auchan site layout may not have this button on the product detail
   page** (observed missing 2026-07-16). If absent, check:
   - whether there is a heart/favourite/bookmark icon nearby,
   - whether the button appears on the search-result card instead,
   - whether the site has a different mechanism entirely.
   If none found, note the item as "nieznaleziony (Dodaj do listy
   niedostepny)" and move on. **Never click "Dodaj do koszyka"** even
   when "Dodaj do listy" is unavailable -- the WAF block applies.
8. If "Dodaj do listy" IS found and clicked: a picker appears with the
   user's lists ("Typowa", "Ulubione", "Kupowane regularnie", "Utworz
   nowa liste"). Click the ref for "Typowa".
9. Navigate to the next item's search URL and repeat.

## Known risks - stop and report, never try to bypass

- **WAF/bot challenge appears anywhere** (not just on cart clicks): stop
  immediately, report to the user, do not retry the same action.
- **CAPTCHA**: stop immediately, report to the user.
- **Session appears logged out** (redirected to login mid-task): stop,
  report - do not attempt to log in again yourself with a hardcoded or
  guessed password.
- **"Dodaj do listy" button missing** from the product page (possible
  site redesign): report affected items as "nieznalezione (przycisk
  niedostepny)" rather than clicking "Dodaj do koszyka" as a fallback.
- **Login script times out**: see login timeout handling in Step 1.
- **Site layout changed** (expected elements/text not found after a
  reasonable look): stop that item, note it as "nieznaleziony" (not
  found) rather than guessing at new selectors, and continue with the
  remaining items.

## Step 4: Report on Telegram (Polish, per SOUL.md - diacritics fine, no emoji/em-dash)

Summarize:
- Dodane do listy Auchan: <lista pozycji>
- Do decyzji (niejednoznaczne): <lista, z krotkim opisem dlaczego>
- Nieznalezione: <lista>
- Przypomnienie: koszyk czeka na reczne "Dodaj wszystko" w Auchan i reczna
  finalizacje zamowienia - nic nie zostalo automatycznie kupione ani
  dodane do koszyka.

## Cleanup

Close the agent-browser session at the end:
```
AB="\$HERMES_HOME/hermes-agent/node_modules/.bin/agent-browser"
$AB close
```
(Or `$AB --session <name> close` if the session is still active.)
Also kill any lingering Chrome processes that may block future logins:
```
pkill -f "agent-browser" 2>/dev/null; pkill -f "chrome" 2>/dev/null
```
