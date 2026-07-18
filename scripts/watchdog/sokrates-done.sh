#!/usr/bin/env bash
# Oznacz komentarz jako zrobiony przez Sokratesa.
# Edytuje treść komentarza na GitHubie: zamienia "@sokrates" na "✅ Zrobione przez Sokratesa"
# Użycie: sokrates-done.sh <comment_id> [repo]
#         Domyślne repo: \$WATCHED_REPO_1

CID="$1"
REPO="${2:-\$WATCHED_REPO_1}"

if [ -z "$CID" ]; then
    echo "Użycie: $0 <comment_id> [repo]" >&2
    echo "  Domyślne repo: \$WATCHED_REPO_1" >&2
    exit 1
fi

CURRENT=$(gh api "repos/$REPO/issues/comments/$CID" --jq '.body' 2>/dev/null)
if [ -z "$CURRENT" ]; then
    echo "❌ Nie znaleziono komentarza $CID w $REPO" >&2
    exit 1
fi

# Jeśli już oznaczony, nie rób nic
if echo "$CURRENT" | grep -q "Zrobione przez Sokratesa"; then
    echo "⚠️  Komentarz $CID już oznaczony jako zrobiony (w $REPO)"
    exit 0
fi

# Zamień @sokrates na marker (case-insensitive)
NEW=$(echo "$CURRENT" | sed 's/@sokrates/✅ Zrobione przez Sokratesa/I')

gh api "repos/$REPO/issues/comments/$CID" \
    -X PATCH -f body="$NEW" --silent 2>&1

echo "✅ Komentarz $CID oznaczony jako zrobiony (w $REPO)"
echo "   $NEW" | head -1