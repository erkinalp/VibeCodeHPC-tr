#!/bin/bash
# SessionStart kancasından başlar, tmux kapanınca otomatik biter

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -n "$TMUX" ]; then
    CURRENT_SESSION=$(tmux display-message -p '#S' 2>/dev/null || echo "")
    
    if [[ "$CURRENT_SESSION" =~ ^(.*)_PM$ ]]; then
        PROJECT_NAME="${BASH_REMATCH[1]}"
    elif [[ "$CURRENT_SESSION" =~ ^(.*)_Workers[0-9]*$ ]]; then
        PROJECT_NAME="${BASH_REMATCH[1]}"
    else
        PROJECT_NAME="Team1"
    fi
else
    PROJECT_NAME="Team1"
fi

PM_SESSION="${PROJECT_NAME}_PM"
WORKER_SESSION="${PROJECT_NAME}_Workers1"

LOG_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor.log"
PID_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor.pid"
CHILD_PID_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor_child.pid"

CONFIG_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor_config.txt"

DEFAULT_UPDATE_INTERVAL_SEC=30  # 30 saniye (üstüne yazma güncelleme sıklığı)
DEFAULT_MILESTONE_INTERVAL_MIN=30  # 30 dakika (kilometre taşı kontrol aralığı)
DEFAULT_MAX_RUNTIME_MIN=1440  # 1440 dakika (1 gün) = 24 * 60
DEFAULT_BUDGET_INTERVAL_MIN=3  # 3 dakika (bütçe toplama aralığı)
DEFAULT_SOTA_INTERVAL_MIN=15  # 15 dakika (SOTA görselleştirme aralığı)

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

UPDATE_INTERVAL_SEC=${UPDATE_INTERVAL_SEC:-$DEFAULT_UPDATE_INTERVAL_SEC}
MILESTONE_INTERVAL_MIN=${MILESTONE_INTERVAL_MIN:-$DEFAULT_MILESTONE_INTERVAL_MIN}
MAX_RUNTIME_MIN=${MAX_RUNTIME_MIN:-$DEFAULT_MAX_RUNTIME_MIN}
BUDGET_INTERVAL_MIN=${BUDGET_INTERVAL_MIN:-$DEFAULT_BUDGET_INTERVAL_MIN}
SOTA_INTERVAL_MIN=${SOTA_INTERVAL_MIN:-$DEFAULT_SOTA_INTERVAL_MIN}

cleanup_existing_processes() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Killing existing monitor process: $OLD_PID" >> "$LOG_FILE"
            kill "$OLD_PID" 2>/dev/null || true
        fi
    fi
    
    if [ -f "$CHILD_PID_FILE" ]; then
        CHILD_PID=$(cat "$CHILD_PID_FILE")
        if kill -0 "$CHILD_PID" 2>/dev/null; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Killing existing child process: $CHILD_PID" >> "$LOG_FILE"
            kill "$CHILD_PID" 2>/dev/null || true
        fi
    fi
}

cleanup_existing_processes

echo $$ > "$PID_FILE"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Periodic monitor started (PID: $$, Project: ${PROJECT_NAME})" >> "$LOG_FILE"
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Monitoring sessions: ${PM_SESSION}, ${WORKER_SESSION}" >> "$LOG_FILE"
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Config: UPDATE_INTERVAL_SEC=${UPDATE_INTERVAL_SEC}s, MILESTONE_INTERVAL_MIN=${MILESTONE_INTERVAL_MIN}min, MAX_RUNTIME_MIN=${MAX_RUNTIME_MIN}min" >> "$LOG_FILE"

get_python_cmd() {
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
    elif command -v python >/dev/null 2>&1; then
        echo "python"
    else
        echo "python3"
    fi
}

PYTHON_CMD=$(get_python_cmd)
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Using Python command: $PYTHON_CMD" >> "$LOG_FILE"

MILESTONES=(30 60 90 120 180)
LAST_MILESTONE=0

PROJECT_START_TIME=""
if [ -f "$PROJECT_ROOT/Agent-shared/project_start_time.txt" ]; then
    PROJECT_START_TIME=$(head -n 1 "$PROJECT_ROOT/Agent-shared/project_start_time.txt" 2>/dev/null || echo "")
fi

get_elapsed_minutes() {
    if [ -n "$PROJECT_START_TIME" ]; then
        START_EPOCH=$(date -d "$PROJECT_START_TIME" +%s 2>/dev/null || echo "0")
        if [ "$START_EPOCH" != "0" ]; then
            CURRENT_EPOCH=$(date +%s)
            echo $(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
        else
            echo "0"
        fi
    else
        echo "0"
    fi
}

cleanup_and_exit() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Monitor terminated" >> "$LOG_FILE"
    if [ -f "$CHILD_PID_FILE" ]; then
        CHILD_PID=$(cat "$CHILD_PID_FILE")
        kill "$CHILD_PID" 2>/dev/null || true
        rm -f "$CHILD_PID_FILE"
    fi
    rm -f "$PID_FILE"
    exit
}
trap cleanup_and_exit TERM INT

START_TIME_FILE="$PROJECT_ROOT/Agent-shared/project_start_time.txt"
if [ ! -f "$START_TIME_FILE" ]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] project_start_time.txt not found, creating..." >> "$LOG_FILE"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$START_TIME_FILE"
fi
START_TIME=$(cat "$START_TIME_FILE")
START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || date -u +%s)

(
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting update subprocess (interval: ${UPDATE_INTERVAL_SEC}s)" >> "$LOG_FILE"
    echo $BASHPID > "$CHILD_PID_FILE"
    
    while true; do
        if ! tmux list-panes -t "$PM_SESSION" 2>/dev/null | grep -q . && \
           ! tmux list-panes -t "$WORKER_SESSION" 2>/dev/null | grep -q .; then
            exit 0
        fi
        
        CURRENT_EPOCH=$(date -u +%s)
        ELAPSED_MINUTES=$(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
        if [ $ELAPSED_MINUTES -gt $MAX_RUNTIME_MIN ]; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Max runtime reached (${MAX_RUNTIME_MIN}min), exiting update loop" >> "$LOG_FILE"
            exit 0
        fi
        
        $PYTHON_CMD "$PROJECT_ROOT/telemetry/context_usage_monitor.py" --graph-type overview 2>&1 | tail -2 >> "$LOG_FILE"
        
        CURRENT_MINUTES=$(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
        
        if [ $((CURRENT_MINUTES % BUDGET_INTERVAL_MIN)) -eq 0 ] && [ -f "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" ]; then
            $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" 2>&1 | tail -1 >> "$LOG_FILE"
        fi
        
        PROJECT_ELAPSED=$(get_elapsed_minutes)
        
        if [ $PROJECT_ELAPSED -eq 5 ] || ([ $PROJECT_ELAPSED -gt 5 ] && [ $((PROJECT_ELAPSED % SOTA_INTERVAL_MIN)) -eq 5 ]); then
            if [ -f "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" ]; then
                echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] SOTA pipeline starting (elapsed=${PROJECT_ELAPSED}min)" >> "$LOG_FILE"
                
                SOTA_TIMEOUT=${SOTA_INTERVAL_MIN}m
                timeout $SOTA_TIMEOUT $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" \
                    --no-delay 2>&1 | tail -5 >> "$LOG_FILE" &
                
                echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] SOTA pipeline launched in background" >> "$LOG_FILE"
            fi
        fi
        
        sleep $UPDATE_INTERVAL_SEC
    done
) &

LAST_MILESTONE=0
MILESTONE_CHECK_INTERVAL=$((MILESTONE_INTERVAL_MIN * 60))  # Dakikayı saniyeye çevir

while true; do
    if ! tmux list-panes -t "$PM_SESSION" 2>/dev/null | grep -q . && \
       ! tmux list-panes -t "$WORKER_SESSION" 2>/dev/null | grep -q .; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] No project tmux sessions found (${PROJECT_NAME}), exiting" >> "$LOG_FILE"
        cleanup_and_exit
    fi
    
    CURRENT_EPOCH=$(date -u +%s)
    ELAPSED_MINUTES=$(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
    
    if [ $ELAPSED_MINUTES -gt $MAX_RUNTIME_MIN ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Max runtime reached (${MAX_RUNTIME_MIN}min), terminating" >> "$LOG_FILE"
        cleanup_and_exit
    fi
    
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Checking milestones... Elapsed: ${ELAPSED_MINUTES} minutes" >> "$LOG_FILE"
    
    for MILESTONE in "${MILESTONES[@]}"; do
        if [ $ELAPSED_MINUTES -ge $MILESTONE ] && [ $LAST_MILESTONE -lt $MILESTONE ]; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Milestone $MILESTONE minutes reached, saving..." >> "$LOG_FILE"
            
            $PYTHON_CMD "$PROJECT_ROOT/telemetry/context_usage_monitor.py" \
                --graph-type overview --max-minutes $MILESTONE 2>&1 | tail -5 >> "$LOG_FILE"
            
            (
                sleep 60  # Yük dağıtımı için 1 dk gecikme
                if [ -f "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" ]; then
                    MILESTONE_TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
                    SNAPSHOT_DIR="$PROJECT_ROOT/Agent-shared/budget/snapshots"
                    mkdir -p "$SNAPSHOT_DIR"
                    
                    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Budget milestone (after_30min) for ${MILESTONE}min" >> "$LOG_FILE"
                    $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" 2>&1 | tail -1 >> "$LOG_FILE"
                    
                    if [ -f "$SNAPSHOT_DIR/latest.json" ]; then
                        cp "$SNAPSHOT_DIR/latest.json" "$SNAPSHOT_DIR/budget_milestone_${MILESTONE}min_${MILESTONE_TIMESTAMP}.json"
                        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Budget milestone saved: budget_milestone_${MILESTONE}min_${MILESTONE_TIMESTAMP}.json" >> "$LOG_FILE"
                    fi
                    
                    GRAPH_PATH="$PROJECT_ROOT/User-shared/visualizations/budget_usage.png"
                    if [ -f "$GRAPH_PATH" ]; then
                        cp "$GRAPH_PATH" "$PROJECT_ROOT/User-shared/visualizations/budget_usage_${MILESTONE}min.png"
                        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Budget graph saved: budget_usage_${MILESTONE}min.png" >> "$LOG_FILE"
                    fi
                fi
            ) &
            
            LAST_MILESTONE=$MILESTONE
        fi
    done
    
    sleep $MILESTONE_CHECK_INTERVAL
done
