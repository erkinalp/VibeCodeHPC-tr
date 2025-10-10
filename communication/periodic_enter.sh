#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage: $0 <PROJECT_NAME>"
    echo "Example: $0 Team1"
    echo "Example: $0 GEMM"
    exit 1
fi

PROJECT_NAME=$1

INTERVAL=${ENTER_INTERVAL:-60}

FLAG_FILE="/tmp/vibecode_periodic_enter_${PROJECT_NAME}.pid"

if [ -f "$FLAG_FILE" ]; then
    OLD_PID=$(cat "$FLAG_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Zaten çalışıyor (PID: $OLD_PID)"
        exit 1
    fi
fi

echo $$ > "$FLAG_FILE"

trap "rm -f $FLAG_FILE; exit" INT TERM EXIT

echo "Periyodik Enter başlatıldı [${PROJECT_NAME}] (${INTERVAL} sn aralık) Durdur: kill $$"

while true; do
    sleep "$INTERVAL"
    
    for session in "${PROJECT_NAME}_PM" "${PROJECT_NAME}_Workers1" "${PROJECT_NAME}_Workers2"; do
        if tmux has-session -t "$session" 2>/dev/null; then
            for pane in $(tmux list-panes -t "$session" -a -F "#{session_name}:#{window_index}.#{pane_index}" 2>/dev/null); do
                if tmux capture-pane -t "$pane" -p | grep -qi "claude"; then
                    tmux send-keys -t "$pane" C-m 2>/dev/null
                fi
            done
        fi
    done
done
