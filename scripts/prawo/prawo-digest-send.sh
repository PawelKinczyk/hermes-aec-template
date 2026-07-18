#!/usr/bin/env bash
# prawo-digest-send - no_agent, zero tokens.
# Delivers the plain-text digest message written by the prawo-digest agent
# step, then clears it. Empty/missing file = silent (no delivery).
MSG_FILE="$HOME/.hermes/state/prawo-digest-message.txt"
if [ -s "$MSG_FILE" ]; then
    cat "$MSG_FILE"
    rm -f "$MSG_FILE"
fi
exit 0
