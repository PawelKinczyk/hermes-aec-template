#!/usr/bin/env bash
# Sokrates executor – odczytuje zadania z pliku i przekazuje do agenta
# Wywoływany przez cronjob co godzinę, z ciszą nocną 23:00-07:59

# Cisza nocna 23:00-07:59
HOUR=$(date +%H)
if [ "$HOUR" -ge 23 ] || [ "$HOUR" -lt 8 ]; then
    exit 0
fi

TASK_FILE="$HOME/.hermes/scripts/.sokrates-tasks.json"

if [ ! -f "$TASK_FILE" ]; then
    echo "BRAK_ZADAŃ"
    exit 0
fi

TASKS=$(cat "$TASK_FILE")
# Sprawdź, czy to pusta lista JSON
if [ "$TASKS" = "[]" ] || [ -z "$TASKS" ]; then
    echo "BRAK_ZADAŃ"
    rm -f "$TASK_FILE"
    exit 0
fi

echo "$TASKS"
# Po odczycie usuń plik (agent sam oznaczy jako zrobione)
rm -f "$TASK_FILE"