#!/bin/bash
# AjanをOpenTelemetry有効でBaşlatmaするヘルパーScript

# Argümanチェック
if [ $# -lt 1 ]; then
    echo "Usage: $0 <AGENT_ID> [additional_claude_options]"
    echo "Example: $0 SE1"
    echo "Example: $0 PG1.1.1 --continue"
    exit 1
fi

AGENT_ID=$1
shift  # 残りの引数はclaude用

# Projeルートの取得
# Ortam değişkeniがAyarされていればそれをKullanım、なければ現在のDizin
if [ -n "$VIBECODE_ROOT" ]; then
    PROJECT_ROOT="$VIBECODE_ROOT"
else
    PROJECT_ROOT="$(pwd)"
fi
TELEMETRY_DIR="$PROJECT_ROOT/telemetry"

# 第2ArgümanがDizinYolの場合、そこに移動
if [ $# -ge 1 ] && [ -d "$PROJECT_ROOT$1" ]; then
    TARGET_DIR="$1"
    echo "📁 Moving to target directory: $TARGET_DIR"
    cd "$PROJECT_ROOT$TARGET_DIR" || {
        echo "❌ Failed to change directory to $PROJECT_ROOT$TARGET_DIR"
        exit 1
    }
    shift  # ディレクトリ引数を除去
fi

# OpenTelemetryAyarDosyaの読み込み
# 優先順位: 1. Projeルート/.env  2. telemetry/otel_config.env  3. telemetry/otel_config.env.example
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    echo "✅ Loaded OpenTelemetry configuration from .env"
elif [ -f "$TELEMETRY_DIR/otel_config.env" ]; then
    source "$TELEMETRY_DIR/otel_config.env"
    echo "✅ Loaded OpenTelemetry configuration from telemetry/otel_config.env"
elif [ -f "$TELEMETRY_DIR/otel_config.env.example" ]; then
    # .envDosyaが存在しない場合は.env.exampleをProjeルートにコピー
    cp "$TELEMETRY_DIR/otel_config.env.example" "$PROJECT_ROOT/.env"
    source "$PROJECT_ROOT/.env"
    echo "✅ Created .env from example and loaded configuration"
else
    echo "⚠️  No OpenTelemetry configuration found, using default configuration"
fi

# GünlükDizinの準備（サブAjan統計用）
SUB_AGENT_LOG_DIR="$TELEMETRY_DIR/sub_agent_logs"
mkdir -p "$SUB_AGENT_LOG_DIR"

# AjanタイプによってプロンプトスタイルをAyar
AGENT_TYPE=$(echo $AGENT_ID | grep -oE '^[A-Z]+')

# 現在の作業Dizinを取得
WORKING_DIR=$(pwd)
# Projeルートからの相対Yol
RELATIVE_DIR=${WORKING_DIR#$PROJECT_ROOT}
RELATIVE_DIR=${RELATIVE_DIR#/}  # 先頭のスラッシュを除去

# チームIDの推定（PG1.1 → team.1, PG2.3 → team.2）
TEAM_ID=$(echo $AGENT_ID | grep -oE '^[A-Z]+[0-9]+(\.[0-9]+)?' | sed 's/^[A-Z]*/team./')

# OTEL_RESOURCE_ATTRIBUTESの更新（agent_id、チーム、作業Dizinを追加）
export OTEL_RESOURCE_ATTRIBUTES="${OTEL_RESOURCE_ATTRIBUTES},agent.id=${AGENT_ID},agent.type=${AGENT_TYPE},team.id=${TEAM_ID},working.dir=${RELATIVE_DIR}"

# Hooksはstart_agent.shでAyarされるため、ここでのAyarは不要

# OTEL_EXPORTER_OTLP_PROTOCOLが未Ayarの場合はデフォルト値をAyar
if [ -z "$OTEL_EXPORTER_OTLP_PROTOCOL" ]; then
    export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
    echo "⚠️  OTEL_EXPORTER_OTLP_PROTOCOL not set, using default: grpc"
fi

# BaşlatmaMesaj
echo "🚀 Starting agent: $AGENT_ID"
echo "📊 OpenTelemetry enabled (OTLP exporter)"
echo ""
echo "Environment:"
echo "  CLAUDE_CODE_ENABLE_TELEMETRY=$CLAUDE_CODE_ENABLE_TELEMETRY"
echo "  OTEL_METRICS_EXPORTER=$OTEL_METRICS_EXPORTER"
echo "  OTEL_EXPORTER_OTLP_PROTOCOL=$OTEL_EXPORTER_OTLP_PROTOCOL"
echo "  OTEL_EXPORTER_OTLP_ENDPOINT=$OTEL_EXPORTER_OTLP_ENDPOINT"
echo "  OTEL_RESOURCE_ATTRIBUTES=$OTEL_RESOURCE_ATTRIBUTES"
echo ""

# bash/zsh対応プロンプトAyar
if [ -n "$ZSH_VERSION" ]; then
    export PROMPT=$'%{\033[1;33m%}('${AGENT_ID}')%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '
elif [ -n "$BASH_VERSION" ]; then
    export PS1="(\[\033[1;33m\]${AGENT_ID}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ "
fi

# サブAjanのエイリアスをAyar
alias claude-p="$TELEMETRY_DIR/claude_p_wrapper.sh"
echo "📊 Sub-agent tracking enabled. Use 'claude-p' instead of 'claude -p'"

# 現在のDizinをKontrol（デバッグ用）
CURRENT_DIR="$(pwd 2>&1)"
if [ $? -ne 0 ]; then
    echo "❌ FATAL ERROR: Cannot determine current directory"
    echo "Error: $CURRENT_DIR"
    echo ""
    echo "This may be caused by:"
    echo "- Directory was deleted while script is running"
    echo "- WSL file system synchronization issue"
    echo "- Directory permissions problem"
    echo ""
    echo "Please check your working directory and try again."
    exit 1
fi

# カスタムİzlemeモード時にstate_monitorをBaşlatma
HOOKS_MODE="${CLI_HOOKS_MODE:-auto}"
if [ "$HOOKS_MODE" = "custom" ] || [ "$HOOKS_MODE" = "hybrid" ]; then
    if [ -n "$TMUX_PANE" ]; then
        echo "🔍 Starting state monitor for $AGENT_ID (pane: $TMUX_PANE)"
        "$TELEMETRY_DIR/state_monitor_tmux.sh" "$AGENT_ID" "$TMUX_PANE" > /dev/null 2>&1 &
        MONITOR_PID=$!
        echo "   Monitor PID: $MONITOR_PID"
    else
        echo "⚠️  Warning: Not in tmux pane, custom hooks monitoring disabled"
    fi
fi

# Claude CodeをBaşlatma
echo "Starting claude with options: --dangerously-skip-permissions $@"
echo "Current directory: $CURRENT_DIR"
echo ""
echo "⚠️  Note: OpenTelemetry metrics are sent to OTLP endpoint"
echo "    Configure your collector at: $OTEL_EXPORTER_OTLP_ENDPOINT"
echo ""

# Claude CodeをBaşlatma（リダイレクトなし）
claude --dangerously-skip-permissions "$@"

# Sonlandırma時のİşleme
echo ""
echo "✅ Agent $AGENT_ID session ended"
echo "📊 Metrics were sent to OTLP endpoint: $OTEL_EXPORTER_OTLP_ENDPOINT"
echo ""
echo "To view metrics, check your configured backend (Grafana, LangFuse, etc.)"