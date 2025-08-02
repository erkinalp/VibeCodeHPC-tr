#!/bin/bash
# PM起動用統合スクリプト
# hooks設定とtelemetry起動を自動化

set -e

# スクリプトのディレクトリからプロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "🎯 OpenCodeAT PM起動スクリプト"
echo "================================"

# 1. PM用のhooks設定
echo "🔧 Setting up hooks for PM..."
if [ -f "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" ]; then
    "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" PM "$PROJECT_ROOT" polling
else
    echo "⚠️  Warning: hooks setup script not found"
fi

# 2. プロジェクト開始時刻を記録（hooksが動作しない場合の保険）
START_TIME_FILE="$PROJECT_ROOT/Agent-shared/project_start_time.txt"
if [ ! -f "$START_TIME_FILE" ] || [ ! -s "$START_TIME_FILE" ]; then
    echo "📅 Recording project start time..."
    mkdir -p "$PROJECT_ROOT/Agent-shared"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$START_TIME_FILE"
fi

# 3. telemetry付きでPM起動
echo "🚀 Starting PM with telemetry..."
echo ""
echo "起動後、以下のプロンプトをコピーして貼り付けてください："
echo "================================================================"
cat << 'EOF'
あなたはPM（Project Manager）です。OpenCodeATプロジェクトを開始します。

まず以下のファイルを読み込んでプロジェクトの全体像を把握してください：
- CLAUDE.md（全エージェント共通ルール）
- instructions/PM.md（あなたの役割詳細）
- requirement_definition.md（プロジェクト要件）※存在する場合
- Agent-shared/以下の全ての.mdと.txtファイル（ただし、.pyファイル、_template、_exampleを除く）

特に重要：
- max_agent_number.txt（利用可能なワーカー数）
- agent_and_pane_id_table.jsonl（セッション構成とエージェント管理）
- directory_map.txt（エージェント配置管理）
- sota_management.md（SOTA管理方法とfamilyの重要性）

全て読み込んだ後、既存の opencodeat セッションを活用してプロジェクトを初期化してください。新規セッションは作成しないでください。
EOF
echo "================================================================"
echo ""

# telemetry起動
exec "$PROJECT_ROOT/telemetry/start_agent_with_telemetry.sh" PM