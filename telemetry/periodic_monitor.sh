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

# 既存のプロセスがあれば終了
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Killing existing monitor process: $OLD_PID" >> "$LOG_FILE"
        kill "$OLD_PID" 2>/dev/null || true
    fi
fi

# 新しいPIDを記録
echo $$ > "$PID_FILE"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Periodic monitor started (PID: $$)" >> "$LOG_FILE"

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
trap 'echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Monitor terminated" >> "$LOG_FILE"; rm -f "$PID_FILE"; exit' TERM INT

# メインループ
while true; do
    # tmuxセッションの存在確認（どれかのVibeCodeHPCセッションが生きているか）
    if ! tmux list-sessions 2>/dev/null | grep -qE "Team1_|pm_session"; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] No tmux sessions found, exiting" >> "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 0
    fi
    
    # プロジェクト開始からの経過時間を計算
    START_TIME_FILE="$PROJECT_ROOT/Agent-shared/project_start_time.txt"
    if [ -f "$START_TIME_FILE" ]; then
        START_TIME=$(cat "$START_TIME_FILE")
        START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || date -u +%s)
        CURRENT_EPOCH=$(date -u +%s)
        ELAPSED_MINUTES=$(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
        
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Elapsed: ${ELAPSED_MINUTES} minutes" >> "$LOG_FILE"
        
        # 概要グラフを常に生成
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Generating overview graph..." >> "$LOG_FILE"
        $PYTHON_CMD "$PROJECT_ROOT/telemetry/context_usage_monitor.py" --graph-type overview 2>&1 | tail -5 >> "$LOG_FILE"
        
        # マイルストーンごとの特別保存
        for MILESTONE in "${MILESTONES[@]}"; do
            if [ $ELAPSED_MINUTES -ge $MILESTONE ] && [ $LAST_MILESTONE -lt $MILESTONE ]; then
                echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Milestone $MILESTONE minutes reached" >> "$LOG_FILE"
                $PYTHON_CMD "$PROJECT_ROOT/telemetry/context_usage_monitor.py" \
                    --graph-type overview --max-minutes $MILESTONE 2>&1 | tail -5 >> "$LOG_FILE"
                LAST_MILESTONE=$MILESTONE
            fi
        done
        
        # SOTA可視化グラフの生成（存在する場合）
        if [ -f "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" ]; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Generating SOTA visualizations..." >> "$LOG_FILE"
            $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" --level project 2>&1 | tail -5 >> "$LOG_FILE"
        fi
    fi
    
    # 30分待機（調整可能）
    sleep 1800
done