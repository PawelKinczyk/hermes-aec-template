#!/usr/bin/env bash
# auchan-login.sh - logs into zakupy.auchan.pl using the encrypted agent-browser
# auth vault ("auchan" profile), never exposing the password to Hermes/Claude
# Code logs or command arguments.
#
# Background: the login submit button is a closed-shadow-DOM Salesforce LWC
# component that no CSS/role/text selector can reach - only an accessibility
# tree ref (from a live snapshot) can click it. agent-browser's own `auth
# login` fills the email/password fields correctly (decrypting internally)
# but then fails at the submit-button step for this exact reason. This script
# completes the click by ref on the same session, right after.
#
# Usage: auchan-login.sh <session-name>
# Exit 0 = confirmed logged in ("Witaj" greeting present, no /login in URL).
# Exit 1 = login failed or could not be confirmed - do not proceed with
#          shopping if this script exits non-zero.

set -uo pipefail

SESSION="${1:?usage: auchan-login.sh <session-name>}"
AB="\$HERMES_HOME/hermes-agent/node_modules/.bin/agent-browser"

# Step 1: fill fields via the encrypted vault. Expected to fail at the
# submit-button step (exit 1, "Timed out waiting for submit button") - any
# OTHER failure (e.g. profile missing, wrong credentials rejected earlier)
# should stop here.
LOGIN_OUT=$("$AB" auth login auchan --session "$SESSION" 2>&1)
LOGIN_EXIT=$?
if [ $LOGIN_EXIT -ne 0 ] && ! grep -q "Timed out waiting for submit button" <<< "$LOGIN_OUT"; then
    echo "BLAD: auth login zakonczyl sie nieoczekiwanym bledem:"
    echo "$LOGIN_OUT"
    exit 1
fi

# Step 2: find the real submit button via a live accessibility snapshot and
# click it by ref (only interaction method that reaches this component).
SNAPSHOT=$("$AB" --session "$SESSION" snapshot 2>&1)
REF=$(grep -oE 'button "Logowanie" \[ref=[a-z0-9]+\]' <<< "$SNAPSHOT" | grep -oE 'ref=[a-z0-9]+' | cut -d= -f2 | head -1)

if [ -z "$REF" ]; then
    echo "BLAD: nie znaleziono przycisku Logowanie w snapshot - struktura strony mogla sie zmienic."
    echo "$SNAPSHOT" | head -20
    exit 1
fi

"$AB" --session "$SESSION" click "@$REF" > /dev/null 2>&1

# Step 3: wait out the multi-hop SSO redirect chain (konto.auchan.pl ->
# ARCD_CIAM_Intermediary -> back to zakupy.auchan.pl), polling instead of a
# fixed sleep since the number of hops can vary.
FINAL_URL=""
for _ in $(seq 1 10); do
    sleep 2
    FINAL_URL=$("$AB" --session "$SESSION" get url 2>&1)
    if [[ "$FINAL_URL" == "https://zakupy.auchan.pl"* ]] && ! grep -qi "login" <<< "$FINAL_URL"; then
        break
    fi
done

if grep -qi "login" <<< "$FINAL_URL" || [[ "$FINAL_URL" != "https://zakupy.auchan.pl"* ]]; then
    echo "BLAD: przekierowanie po logowaniu nie dokonczylo sie w oczekiwanym czasie ($FINAL_URL)."
    exit 1
fi

PAGE_TEXT=$("$AB" --session "$SESSION" eval "document.body.innerText" 2>&1)
if ! grep -qi "Witaj" <<< "$PAGE_TEXT"; then
    echo "OSTRZEZENIE: brak powitania 'Witaj X' na stronie - zaloguj sie recznie i zweryfikuj (URL: $FINAL_URL)."
    exit 1
fi

echo "OK: zalogowano pomyslnie (sesja: $SESSION, URL: $FINAL_URL)"
exit 0
