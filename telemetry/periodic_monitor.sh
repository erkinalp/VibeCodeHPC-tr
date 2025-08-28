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
DEFAULT_BUDGET_INTERVAL_MIN=3  # 3分（予算集計間隔）

# 設定読み込み（存在すれば）
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# 変数初期化（オーバライド可能）
UPDATE_INTERVAL_SEC=${UPDATE_INTERVAL_SEC:-$DEFAULT_UPDATE_INTERVAL_SEC}
MILESTONE_INTERVAL_MIN=${MILESTONE_INTERVAL_MIN:-$DEFAULT_MILESTONE_INTERVAL_MIN}
MAX_RUNTIME_MIN=${MAX_RUNTIME_MIN:-$DEFAULT_MAX_RUNTIME_MIN}
BUDGET_INTERVAL_MIN=${BUDGET_INTERVAL_MIN:-$DEFAULT_BUDGET_INTERVAL_MIN}

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

# マイルストーン時間（分）
MILESTONES=(30 60 90 120 180)
LAST_MILESTONE=0

# プロジェクト開始時刻を読み取り
PROJECT_START_TIME=""
if [ -f "$PROJECT_ROOT/Agent-shared/project_start_time.txt" ]; then
    PROJECT_START_TIME=$(head -n 1 "$PROJECT_ROOT/Agent-shared/project_start_time.txt" 2>/dev/null || echo "")
fi

# プロジェクト開始からの経過分数を計算
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
        
        # 予算集計とSOTA可視化を時間差実行（負荷分散）
        CURRENT_MINUTES=$(( (CURRENT_EPOCH - START_EPOCH) / 60 ))
        
        # 予算集計: 3分間隔（元のまま）
        if [ $((CURRENT_MINUTES % BUDGET_INTERVAL_MIN)) -eq 0 ] && [ -f "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" ]; then
            $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" 2>&1 | tail -1 >> "$LOG_FILE"
        fi
        
        # SOTA可視化: 30分ごとに分散実行（30-45分の間で複数のレベルを順次生成）
        # プロジェクト開始からの経過時間を基準に、相対時刻でグラフを生成
        PROJECT_ELAPSED=$(get_elapsed_minutes)
        if [ "$PROJECT_ELAPSED" -gt 0 ]; then
            # 30分ごとのマイルストーンを基準に、そこから0-15分の間で分散
            MILESTONE_BASE=$((PROJECT_ELAPSED / 30 * 30))  # 30, 60, 90...
            OFFSET_FROM_MILESTONE=$((PROJECT_ELAPSED - MILESTONE_BASE))
            
            # 0-15分の間で異なるレベルのグラフを生成
            if [ $OFFSET_FROM_MILESTONE -ge 2 ] && [ $OFFSET_FROM_MILESTONE -lt 17 ]; then
                SOTA_CMD=""
                case $OFFSET_FROM_MILESTONE in
                    2|3)  # 32-33分: projectレベル
                        SOTA_CMD="--level project --x-axis time"
                        ;;
                    5|6)  # 35-36分: localレベル
                        SOTA_CMD="--level local --x-axis time"
                        ;;
                    8|9)  # 38-39分: familyレベル（全て）
                        SOTA_CMD="--level family --x-axis time"
                        ;;
                    11|12) # 41-42分: hardwareレベル
                        SOTA_CMD="--level hardware --x-axis time"
                        ;;
                    14|15) # 44-45分: カウントベース
                        SOTA_CMD="--level project --x-axis count"
                        ;;
                esac
                
                # 効率化版を優先的に使用
                if [ -n "$SOTA_CMD" ]; then
                    if [ -f "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer_efficient.py" ]; then
                        # 効率化版がある場合はそれを使用（レベルごとに一括生成）
                        LEVEL_ONLY=$(echo $SOTA_CMD | grep -oP '(?<=--level )\w+')
                        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] SOTA efficient: level=$LEVEL_ONLY (elapsed=${PROJECT_ELAPSED}min)" >> "$LOG_FILE"
                        $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer_efficient.py" --level $LEVEL_ONLY 2>&1 | tail -2 >> "$LOG_FILE"
                    elif [ -f "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" ]; then
                        # 従来版へのフォールバック
                        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] SOTA vis: $SOTA_CMD (elapsed=${PROJECT_ELAPSED}min)" >> "$LOG_FILE"
                        $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/sota/sota_visualizer.py" $SOTA_CMD 2>&1 | tail -2 >> "$LOG_FILE"
                    fi
                fi
            fi
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
            
            # コンテキスト使用率のマイルストーン保存（visualizations直下のみ）
            # 注: context_usage_monitor.pyは自動的にvisualizations/context_usage_${MILESTONE}min.pngを生成
            $PYTHON_CMD "$PROJECT_ROOT/telemetry/context_usage_monitor.py" \
                --graph-type overview --max-minutes $MILESTONE 2>&1 | tail -5 >> "$LOG_FILE"
            
            # 予算集計のマイルストーン保存（after_30min: 1分遅延）
            (
                sleep 60  # 1分遅延で負荷分散
                if [ -f "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" ]; then
                    MILESTONE_TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
                    SNAPSHOT_DIR="$PROJECT_ROOT/Agent-shared/budget/snapshots"
                    mkdir -p "$SNAPSHOT_DIR"
                    
                    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Budget milestone (after_30min) for ${MILESTONE}min" >> "$LOG_FILE"
                    $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" 2>&1 | tail -1 >> "$LOG_FILE"
                    
                    # マイルストーン時点の別名保存
                    if [ -f "$SNAPSHOT_DIR/latest.json" ]; then
                        cp "$SNAPSHOT_DIR/latest.json" "$SNAPSHOT_DIR/budget_milestone_${MILESTONE}min_${MILESTONE_TIMESTAMP}.json"
                        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Budget milestone saved: budget_milestone_${MILESTONE}min_${MILESTONE_TIMESTAMP}.json" >> "$LOG_FILE"
                    fi
                    
                    # マイルストーン時点のグラフも別名保存
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
    
    # マイルストーン確認間隔で待機
    sleep $MILESTONE_CHECK_INTERVAL
done