#!/bin/bash
# エージェントをOpenTelemetry有効で起動するヘルパースクリプト

# 引数チェック
if [ $# -lt 1 ]; then
    echo "Usage: $0 <AGENT_ID> [additional_claude_options]"
    echo "Example: $0 SE1"
    echo "Example: $0 PG1.1.1 --continue"
    exit 1
fi

AGENT_ID=$1
shift  # 残りの引数はclaude用

# プロジェクトルートの取得
# 環境変数が設定されていればそれを使用、なければスクリプトの場所から推定
if [ -n "$OPENCODEAT_ROOT" ]; then
    PROJECT_ROOT="$OPENCODEAT_ROOT"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
fi
TELEMETRY_DIR="$PROJECT_ROOT/telemetry"

# ログファイルの準備
LOG_DIR="$TELEMETRY_DIR/raw_metrics"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/agent_${AGENT_ID}_$(date +%Y%m%d_%H%M%S).log"

# エージェントタイプによってプロンプトスタイルを設定
AGENT_TYPE=$(echo $AGENT_ID | grep -oE '^[A-Z]+')

# 現在の作業ディレクトリを取得
WORKING_DIR=$(pwd)
# プロジェクトルートからの相対パス
RELATIVE_DIR=${WORKING_DIR#$PROJECT_ROOT}
RELATIVE_DIR=${RELATIVE_DIR#/}  # 先頭のスラッシュを除去

# OTEL_RESOURCE_ATTRIBUTESの更新（agent_id、作業ディレクトリを追加）
export OTEL_RESOURCE_ATTRIBUTES="${OTEL_RESOURCE_ATTRIBUTES},agent_id=${AGENT_ID},agent_type=${AGENT_TYPE},working_dir=${RELATIVE_DIR}"

# auto-compactフックの設定確認
SETTINGS_FILE="$HOME/.claude/settings.json"
if [ ! -f "$SETTINGS_FILE" ] || ! grep -q "PreCompact" "$SETTINGS_FILE"; then
    echo "⚠️  Auto-compact hook not configured. Setting up..."
    python "$TELEMETRY_DIR/setup_auto_compact_hook.py" --agent-id "$AGENT_ID"
fi

# 起動メッセージ
echo "🚀 Starting agent: $AGENT_ID"
echo "📊 OpenTelemetry enabled"
echo "📝 Logging to: $LOG_FILE"
echo ""
echo "Environment:"
echo "  CLAUDE_CODE_ENABLE_TELEMETRY=$CLAUDE_CODE_ENABLE_TELEMETRY"
echo "  OTEL_METRICS_EXPORTER=$OTEL_METRICS_EXPORTER"
echo "  OTEL_METRIC_EXPORT_INTERVAL=$OTEL_METRIC_EXPORT_INTERVAL"
echo "  OTEL_RESOURCE_ATTRIBUTES=$OTEL_RESOURCE_ATTRIBUTES"
echo ""

# プロンプトスタイルの更新
export PS1="(\[\033[1;33m\]${AGENT_ID}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ "

# Claude Codeを起動（出力をログファイルにも記録）
echo "Starting claude with options: --dangerously-skip-permissions $@"
claude --dangerously-skip-permissions "$@" 2>&1 | tee "$LOG_FILE"

# 終了時の処理
echo ""
echo "✅ Agent $AGENT_ID session ended"
echo "📊 Metrics saved to: $LOG_FILE"
echo ""
echo "To analyze metrics, run:"
echo "  python $TELEMETRY_DIR/collect_metrics.py $LOG_FILE $AGENT_ID"