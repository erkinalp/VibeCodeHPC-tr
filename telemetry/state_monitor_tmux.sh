#!/bin/bash

if [ $# -lt 2 ]; then
    echo "Usage: $0 <AGENT_ID> <PANE_ID>"
    exit 1
fi

AGENT_ID=$1
PANE_ID=$2

if [ -n "$VIBECODE_ROOT" ]; then
    PROJECT_ROOT="$VIBECODE_ROOT"
else
    PROJECT_ROOT="$(pwd)"
fi

STATE="idle"
PENDING_STATE="idle"
PENDING_START=0
STATE_PERSISTENCE_MS=200

# session_id alma (agent_and_pane_id_table.jsonl’den)
get_session_id() {
    if [ -f "$PROJECT_ROOT/Agent-shared/agent_and_pane_id_table.jsonl" ]; then
        grep "\"agent_id\":\"$AGENT_ID\"" "$PROJECT_ROOT/Agent-shared/agent_and_pane_id_table.jsonl" | \
            tail -1 | \
            grep -oP '"claude_session_id":"\K[^"]*'
    fi
}

detect_state() {
    local content="$1"
    local content_lower=$(echo "$content" | tr '[:upper:]' '[:lower:]')

    # waiting
    if echo "$content" | grep -qE "│ do you want|│ would you like"; then
        echo "waiting"
        return
    fi

    # busy
    if echo "$content_lower" | grep -q "esc to interrupt"; then
        echo "busy"
        return
    fi

    echo "idle"
}

on_state_changed() {
    local old_state="$1"
    local new_state="$2"

    if [ "$new_state" = "idle" ] && [ "$old_state" != "idle" ]; then
        if [ -f ".claude/hooks/stop.py" ]; then
            echo "[state_monitor] Calling Stop hook"
            echo '{}' | python3 ".claude/hooks/stop.py" 2>/dev/null || true
        fi
    fi
}

echo "[state_monitor] Starting for $AGENT_ID (pane: $PANE_ID)"

# SessionStart hook’unu çalıştır (yalnız başlangıçta 1 kez)
if [ -f ".claude/hooks/session_start.py" ]; then
    echo "[state_monitor] Calling SessionStart hook"
    echo '{}' | python3 ".claude/hooks/session_start.py" 2>/dev/null || true
fi

# PostToolUse izleme için son kontrol zamanı
LAST_TOOL_CHECK=0

check_post_tool_use() {
    # session_id al
    local session_id=$(get_session_id)
    if [ -z "$session_id" ]; then
        return
    fi

    local home_dir=$(eval echo ~$(whoami))
    local jsonl_pattern="$home_dir/.claude/projects/*/${session_id}.jsonl"
    local jsonl_file=$(ls $jsonl_pattern 2>/dev/null | head -1)

    if [ ! -f "$jsonl_file" ]; then
        return
    fi

    local recent_tools=$(tail -10 "$jsonl_file" 2>/dev/null | grep -o '"type":"tool_use".*"name":"Bash"' | tail -1)

    if [ -n "$recent_tools" ]; then
        # Bash tool_use saptanırsa post_tool_ssh_handler.py’yi çağır
        if [ -f ".claude/hooks/post_tool_ssh_handler.py" ]; then
            echo "[state_monitor] Detected Bash tool use, calling PostToolUse hook"
            tail -10 "$jsonl_file" 2>/dev/null | grep '"type":"tool_use"' | tail -1 | python3 ".claude/hooks/post_tool_ssh_handler.py" 2>/dev/null || true
        fi
    fi
}

while true; do
    # tmux pane var mı kontrol et
    if ! tmux list-panes -t "$PANE_ID" >/dev/null 2>&1; then
        echo "[state_monitor] Pane $PANE_ID not found, exiting"
        break
    fi

    OUTPUT=$(tmux capture-pane -p -S -30 -E -1 -t "$PANE_ID" 2>/dev/null || echo "")

    if [ -n "$OUTPUT" ]; then
        DETECTED=$(detect_state "$OUTPUT")
        NOW=$(date +%s%3N 2>/dev/null || echo "0")

        # PostToolUse izleme (5 saniyede bir)
        if [ "$NOW" != "0" ]; then
            if [ $((NOW - LAST_TOOL_CHECK)) -ge 5000 ]; then
                check_post_tool_use
                LAST_TOOL_CHECK=$NOW
            fi
        fi

        if [ "$DETECTED" != "$PENDING_STATE" ]; then
            PENDING_STATE="$DETECTED"
            PENDING_START=$NOW
        else
            if [ "$NOW" != "0" ]; then
                DURATION=$((NOW - PENDING_START))
                if [ $DURATION -ge $STATE_PERSISTENCE_MS ] && [ "$STATE" != "$DETECTED" ]; then
                    OLD_STATE="$STATE"
                    STATE="$DETECTED"
                    echo "[state_monitor] State changed: $OLD_STATE → $STATE"
                    on_state_changed "$OLD_STATE" "$STATE"
                fi
            fi
        fi
    fi

    sleep 0.1
done

echo "[state_monitor] Stopped for $AGENT_ID"
