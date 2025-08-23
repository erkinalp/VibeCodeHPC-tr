#!/bin/bash
# 定期的にcontext_usage_monitor.pyを実行するバックグラウンドスクリプト
# SessionStartフックから起動され、tmux解除で自動終了

set -e

# プロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ログファイル
LOG_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor.log"
PID_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor.pid"
CHILD_PID_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor_child.pid"

# 設定ファイル（ユーザがオーバライド可能）
CONFIG_FILE="$PROJECT_ROOT/Agent-shared/periodic_monitor_config.txt"

# デフォルト値
DEFAULT_UPDATE_INTERVAL_SEC=30  # 30秒（上書き更新頻度）
DEFAULT_MILESTONE_INTERVAL_MIN=30  # 30分（マイルストーン確認間隔）
DEFAULT_MAX_RUNTIME_MIN=4320  # 4320分（3日）= 24 * 60 * 3

# 設定読み込み（存在すれば）
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# 変数初期化（オーバライド可能）
UPDATE_INTERVAL_SEC=${UPDATE_INTERVAL_SEC:-$DEFAULT_UPDATE_INTERVAL_SEC}
MILESTONE_INTERVAL_MIN=${MILESTONE_INTERVAL_MIN:-$DEFAULT_MILESTONE_INTERVAL_MIN}
MAX_RUNTIME_MIN=${MAX_RUNTIME_MIN:-$DEFAULT_MAX_RUNTIME_MIN}

# 既存のプロセスがあれば終了
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

# 新しいPIDを記録
echo $$ > "$PID_FILE"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Periodic monitor started (PID: $$)" >> "$LOG_FILE"
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Config: UPDATE_INTERVAL_SEC=${UPDATE_INTERVAL_SEC}s, MILESTONE_INTERVAL_MIN=${MILESTONE_INTERVAL_MIN}min, MAX_RUNTIME_MIN=${MAX_RUNTIME_MIN}min" >> "$LOG_FILE"

# Python実行コマンドを決定
get_python_cmd() {
    if command -v uv >/dev/null 2>&1; then
        echo "uv run"
    elif command -v uvx >/dev/null 2>&1; then
        echo "uvx"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    elif command -v python >/dev/null 2>&1; then
        echo "python"
    else
        echo "python"
    fi
}

PYTHON_CMD=$(get_python_cmd)
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Using Python command: $PYTHON_CMD" >> "$LOG_FILE"

# マイルストーン時間（分）
MILESTONES=(30 60 90 120 180)
LAST_MILESTONE=0

# tmuxセッションが終了したら自動終了
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

# プロジェクト開始時刻を取得
START_TIME_FILE="$PROJECT_ROOT/Agent-shared/project_start_time.txt"
if [ ! -f "$START_TIME_FILE" ]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] project_start_time.txt not found, creating..." >> "$LOG_FILE"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$START_TIME_FILE"
fi
START_TIME=$(cat "$START_TIME_FILE")
START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || date -u +%s)

# サブプロセス1: 高頻度更新（上書き版）
(
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting update subprocess (interval: ${UPDATE_INTERVAL_SEC}s)" >> "$LOG_FILE"
    echo $BASHPID > "$CHILD_PID_FILE"
    
    while true; do
        # tmuxセッション確認（任意のセッション名に対応）
        if ! tmux list-sessions 2>/dev/null | grep -q .; then
            # セッションが1つも存在しない場合のみ終了
            exit 0
        fi
        
        # 最大実行時間チェック
        CURRENT_EPOCH=$(date -u +%s)
        ELAPSED_MINUTES=$(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
        if [ $ELAPSED_MINUTES -gt $MAX_RUNTIME_MIN ]; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Max runtime reached (${MAX_RUNTIME_MIN}min), exiting update loop" >> "$LOG_FILE"
            exit 0
        fi
        
        # 上書き版のグラフ生成（簡潔なログ）
        $PYTHON_CMD "$PROJECT_ROOT/telemetry/context_usage_monitor.py" --graph-type overview 2>&1 | tail -2 >> "$LOG_FILE"
        
        # SOTA可視化（存在する場合、全レベル一括生成）
        if [ -f "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" ]; then
            $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" --level all 2>&1 | tail -2 >> "$LOG_FILE"
        fi
        
        sleep $UPDATE_INTERVAL_SEC
    done
) &

# メインプロセス: マイルストーン保存
LAST_MILESTONE=0
MILESTONE_CHECK_INTERVAL=$((MILESTONE_INTERVAL_MIN * 60))  # 分を秒に変換

while true; do
    # tmuxセッション確認（任意のセッション名に対応）
    if ! tmux list-sessions 2>/dev/null | grep -q .; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] No tmux sessions found, exiting" >> "$LOG_FILE"
        cleanup_and_exit
    fi
    
    # 経過時間計算
    CURRENT_EPOCH=$(date -u +%s)
    ELAPSED_MINUTES=$(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
    
    # 最大実行時間チェック
    if [ $ELAPSED_MINUTES -gt $MAX_RUNTIME_MIN ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Max runtime reached (${MAX_RUNTIME_MIN}min), terminating" >> "$LOG_FILE"
        cleanup_and_exit
    fi
    
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Checking milestones... Elapsed: ${ELAPSED_MINUTES} minutes" >> "$LOG_FILE"
    
    # マイルストーンごとの特別保存
    for MILESTONE in "${MILESTONES[@]}"; do
        if [ $ELAPSED_MINUTES -ge $MILESTONE ] && [ $LAST_MILESTONE -lt $MILESTONE ]; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Milestone $MILESTONE minutes reached, saving..." >> "$LOG_FILE"
            $PYTHON_CMD "$PROJECT_ROOT/telemetry/context_usage_monitor.py" \
                --graph-type overview --max-minutes $MILESTONE 2>&1 | tail -5 >> "$LOG_FILE"
            LAST_MILESTONE=$MILESTONE
        fi
    done
    
    # マイルストーン確認間隔で待機
    sleep $MILESTONE_CHECK_INTERVAL
done