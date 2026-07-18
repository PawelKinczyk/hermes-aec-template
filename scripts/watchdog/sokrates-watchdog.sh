#!/usr/bin/env bash
# Sokrates watchdog – sprawdza nowe wzmianki @sokrates w issue i komentarzach
# w wielu repozytoriach.
# stdout pusty = cisza, stdout ≠ pusty = dostawa do użytkownika
#
# ANTI-LOOP: po odpowiedzi edytuj oryginalny komentarz i zamień @sokrates
#            na "✅ Zrobione przez Sokratesa". Watchdog pomija takie komentarze.

REPOS=("\$WATCHED_REPO_1" "\$WATCHED_REPO_2" "\$WATCHED_REPO_3")
SCRIPT_DIR="$HOME/.hermes/scripts"
STATE_FILE="$SCRIPT_DIR/.sokrates-last-check"
TMPDIR=$(mktemp -d /tmp/sokrates-XXXXXX)
trap "rm -rf $TMPDIR" EXIT

NOW=$(date -u +%s)
if [ -f "$STATE_FILE" ]; then
    SINCE=$(cat "$STATE_FILE")
else
    SINCE=$((NOW - 7200))
fi
echo "$NOW" > "$STATE_FILE"

SINCE_ISO=$(date -u -d "@$SINCE" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -r "$SINCE" +%Y-%m-%dT%H:%M:%SZ)

HAD_OUTPUT=0
for REPO in "${REPOS[@]}"; do
    ISSUES_FILE="$TMPDIR/issues-$(echo "$REPO" | tr '/' '-').json"
    COMMENTS_FILE="$TMPDIR/comments-$(echo "$REPO" | tr '/' '-').json"

    # Pobierz dane
    gh api "repos/$REPO/issues?since=$SINCE_ISO&state=open&per_page=20" > "$ISSUES_FILE" 2>/dev/null
    gh api "repos/$REPO/issues/comments?since=$SINCE_ISO&per_page=30" > "$COMMENTS_FILE" 2>/dev/null

    # Jeśli któryś plik jest pusty lub [] to pomijamy
    ISSUE_COUNT=$(python3 -c "import json; d=json.load(open('$ISSUES_FILE')); print(len([i for i in d if 'pull_request' not in i]))" 2>/dev/null || echo 0)
    COMMENT_COUNT=$(python3 -c "import json; d=json.load(open('$COMMENTS_FILE')); print(len(d))" 2>/dev/null || echo 0)

    if [ "$ISSUE_COUNT" -gt 0 ] || [ "$COMMENT_COUNT" -gt 0 ]; then
        python3 "$SCRIPT_DIR/sokrates-filter.py" "$ISSUES_FILE" "$COMMENTS_FILE" "$REPO"
        FILTER_EXIT=$?
        # FILTER_EXIT nie jest używany – stdout mówi sam za siebie
        :
    fi
done

# Zawsze exit 0 – cronjob no_agent dostarcza stdout gdy niepusty,
# a non-zero exit byłby traktowany jako błąd skryptu
exit 0