#!/usr/bin/env bash
# auchan-search-add.sh <session> <list-name> <query>
#
# Searches zakupy.auchan.pl for <query>, opens the first result, and adds it
# to Auchan list <list-name> via "Dodaj do listy" (creating the list first if
# it does not exist yet). Never touches "Dodaj do koszyka" (cart) - that
# action is protected by bot detection (AWS WAF) and must never be clicked
# by automation (verified 2026-07-16).
#
# Assumes <session> is already logged in via auchan-login.sh.
#
# Output contract (stdout, one line, plus exit code):
#   "ADDED: <product name>"   exit 0  - success
#   "NOT_FOUND: <query>"      exit 1  - no search results at all
#   "ERROR: <details>"        exit 1  - unexpected failure (layout changed,
#                                       WAF/captcha, missing element, etc.)
#                                       Never retried automatically by the
#                                       caller - surface to the user.

set -uo pipefail

SESSION="${1:?usage: auchan-search-add.sh <session> <list-name> <query>}"
LIST_NAME="${2:?usage: auchan-search-add.sh <session> <list-name> <query>}"
QUERY="${3:?usage: auchan-search-add.sh <session> <list-name> <query>}"
AB="\$HERMES_HOME/hermes-agent/node_modules/.bin/agent-browser"

close_popups() {
    local snap ref
    snap=$("$AB" --session "$SESSION" snapshot -c 2>&1)
    ref=$(grep -oE '(button "Zamknij[^"]*"|button "Akceptuję wszystkie") \[ref=[a-z0-9]+\]' <<< "$snap" \
        | grep -oE 'ref=[a-z0-9]+' | head -1 | cut -d= -f2)
    if [ -n "$ref" ]; then
        "$AB" --session "$SESSION" click "@$ref" > /dev/null 2>&1
        sleep 1
    fi
}

ref_of() {
    # $1 = grep -oE pattern that must capture exactly one "ref=xxx" group
    grep -oE "$1" | grep -oE 'ref=[a-z0-9]+' | head -1 | cut -d= -f2
}

ENCODED_QUERY=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$QUERY")

"$AB" --session "$SESSION" open "https://zakupy.auchan.pl/search?q=$ENCODED_QUERY" > /dev/null 2>&1
sleep 2
close_popups

SNAP=$("$AB" --session "$SESSION" snapshot -c 2>&1)

if grep -qiE "captcha|access denied|zostales zablokowany" <<< "$SNAP"; then
    echo "ERROR: mozliwe wyzwanie antybotowe lub blokada - przerwano, nie ponawiac"
    exit 1
fi

BTN_LINE_NUM=$(grep -n 'button "Dodaj produkt .* do koszyka"' <<< "$SNAP" | head -1 | cut -d: -f1)
if [ -z "$BTN_LINE_NUM" ]; then
    echo "NOT_FOUND: $QUERY"
    exit 1
fi

FIRST_BUTTON_LINE=$(sed -n "${BTN_LINE_NUM}p" <<< "$SNAP")
PRODUCT_NAME=$(sed -E 's/.*button "Dodaj produkt (.+) do koszyka".*/\1/' <<< "$FIRST_BUTTON_LINE")

# Only search the ~15 lines immediately BEFORE this button for the matching
# product link - the same name can appear elsewhere on the page (e.g. a
# personalized "Ulubione"/favorites carousel), and a plain whole-page search
# can grab the wrong link entirely (verified 2026-07-16).
WINDOW_START=$(( BTN_LINE_NUM > 15 ? BTN_LINE_NUM - 15 : 1 ))
LINK_REF=$(sed -n "${WINDOW_START},${BTN_LINE_NUM}p" <<< "$SNAP" | grep -F "link \"$PRODUCT_NAME\"" | ref_of 'ref=[a-z0-9]+')
if [ -z "$LINK_REF" ]; then
    echo "ERROR: znaleziono produkt '$PRODUCT_NAME' ale brak linku do strony produktu w poblizu - struktura strony mogla sie zmienic"
    exit 1
fi

"$AB" --session "$SESSION" click "@$LINK_REF" > /dev/null 2>&1
sleep 2
close_popups

# Some product cards redirect to an unrelated promo/interstitial page instead
# of the product page (observed 2026-07-16, e.g. certain fresh-dairy items) -
# verify we actually landed on a /products/ page before looking for the
# "Dodaj do listy" button, so the error message is accurate.
LANDED_URL=$("$AB" --session "$SESSION" get url 2>&1)
if [[ "$LANDED_URL" != *"/products/"* ]]; then
    echo "ERROR: kliknięcie w '$PRODUCT_NAME' nie doprowadziło do strony produktu (trafiono na $LANDED_URL) - pomijam ten produkt"
    exit 1
fi

SNAP2=$("$AB" --session "$SESSION" snapshot -c 2>&1)
LIST_BTN_REF=$(grep -oE 'button "Dodaj do listy" \[ref=[a-z0-9]+\]' <<< "$SNAP2" | ref_of 'ref=[a-z0-9]+')
if [ -z "$LIST_BTN_REF" ]; then
    echo "ERROR: brak przycisku 'Dodaj do listy' na stronie produktu '$PRODUCT_NAME' - struktura strony mogla sie zmienic"
    exit 1
fi

"$AB" --session "$SESSION" click "@$LIST_BTN_REF" > /dev/null 2>&1
sleep 1

SNAP3=$("$AB" --session "$SESSION" snapshot -c 2>&1)
EXISTING_REF=$(grep -oE "button \"${LIST_NAME} Dodaj[^\"]*\" \[ref=[a-z0-9]+\]" <<< "$SNAP3" | ref_of 'ref=[a-z0-9]+')

if [ -n "$EXISTING_REF" ]; then
    "$AB" --session "$SESSION" click "@$EXISTING_REF" > /dev/null 2>&1
else
    CREATE_REF=$(grep -oE 'button "Utwórz nową listę" \[ref=[a-z0-9]+\]' <<< "$SNAP3" | ref_of 'ref=[a-z0-9]+')
    if [ -z "$CREATE_REF" ]; then
        echo "ERROR: brak opcji tworzenia listy w oknie wyboru - struktura strony mogla sie zmienic"
        exit 1
    fi
    "$AB" --session "$SESSION" click "@$CREATE_REF" > /dev/null 2>&1
    sleep 1

    SNAP4=$("$AB" --session "$SESSION" snapshot -c 2>&1)
    NAME_INPUT_REF=$(grep -oE 'textbox "Nazwa listy" \[required, ref=[a-z0-9]+\]' <<< "$SNAP4" | ref_of 'ref=[a-z0-9]+')
    CREATE_BTN_REF=$(grep -oE 'button "Utwórz listę" \[ref=[a-z0-9]+\]' <<< "$SNAP4" | ref_of 'ref=[a-z0-9]+')
    if [ -z "$NAME_INPUT_REF" ] || [ -z "$CREATE_BTN_REF" ]; then
        echo "ERROR: brak formularza tworzenia listy - struktura strony mogla sie zmienic"
        exit 1
    fi

    "$AB" --session "$SESSION" fill "@$NAME_INPUT_REF" "$LIST_NAME" > /dev/null 2>&1
    "$AB" --session "$SESSION" click "@$CREATE_BTN_REF" > /dev/null 2>&1
    sleep 2

    SNAP5=$("$AB" --session "$SESSION" snapshot -c 2>&1)
    NEW_LIST_REF=$(grep -oE "button \"${LIST_NAME} Dodaj[^\"]*\" \[ref=[a-z0-9]+\]" <<< "$SNAP5" | ref_of 'ref=[a-z0-9]+')
    if [ -z "$NEW_LIST_REF" ]; then
        echo "ERROR: lista '$LIST_NAME' zostala prawdopodobnie utworzona, ale nie udalo sie potwierdzic dodania produktu do niej"
        exit 1
    fi
    "$AB" --session "$SESSION" click "@$NEW_LIST_REF" > /dev/null 2>&1
fi

sleep 1
echo "ADDED: $PRODUCT_NAME"
exit 0
