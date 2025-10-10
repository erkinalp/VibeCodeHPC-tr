#!/bin/bash
# AjanBaşlatma用Script（シンプル版）
# PMがKullanım：各Ajanを適切な場所でClaudeBaşlatma

if [ $# -lt 2 ]; then
    echo "Usage: $0 <AGENT_ID> <TARGET_DIR> [additional_options]"
    echo "Example: $0 PG1.1.1 /Flow/TypeII/single-node/intel2024/OpenMP"
    echo ""
    echo "Environment variables:"
    echo "  VIBECODE_ENABLE_TELEMETRY=false  # テレメトリを無効化"
    echo "  VIBECODE_ENABLE_HOOKS=false      # hooks無効化（非推奨）"
    exit 1
fi

AGENT_ID=$1
TARGET_DIR=$2
shift 2
ADDITIONAL_OPTIONS="$@"

# 現在のDizin（Projeルート）を取得
PROJECT_ROOT="$(pwd)"

# agent_and_pane_id_table.jsonlでAjanIDをKontrol
TABLE_FILE="$PROJECT_ROOT/Agent-shared/agent_and_pane_id_table.jsonl"
if [ -f "$TABLE_FILE" ]; then
    # AGENT_IDが「待機中」で始まるかチェック
    if [[ "$AGENT_ID" =~ ^待機中 ]]; then
        echo "❌ エラー: エージェントIDが「待機中」のままです"
        echo "   先にagent_and_pane_id_table.jsonlのagent_idを正しいID（例: PG1.1.3）に更新してください"
        echo ""
        echo "   例: 「待機中3」→「PG1.1.3」"
        echo ""
        echo "   その後、正しいIDでこのコマンドを実行してください："
        echo "   ./communication/start_agent.sh PG1.1.3 $TARGET_DIR"
        exit 1
    fi
    
    # テーブルに存在するかKontrol（jqがある場合のみ）
    if command -v jq &> /dev/null; then
        if ! grep -q "\"agent_id\":[[:space:]]*\"$AGENT_ID\"" "$TABLE_FILE"; then
            echo "⚠️  警告: agent_and_pane_id_table.jsonlに $AGENT_ID が見つかりません"
            echo "   テーブルにエージェントIDを追加してから実行することを推奨します"
        fi
    fi
fi

echo "🚀 Starting agent $AGENT_ID at $TARGET_DIR"

# 1. ProjeルートをOrtam değişkeniとしてAyar
./communication/agent_send.sh "$AGENT_ID" "export VIBECODE_ROOT='$PROJECT_ROOT'"

# CLI_HOOKS_MODEをOrtam değişkeniとしてAyar（未Ayar時はauto）
CLI_HOOKS_MODE="${CLI_HOOKS_MODE:-auto}"
./communication/agent_send.sh "$AGENT_ID" "export CLI_HOOKS_MODE='$CLI_HOOKS_MODE'"

# 2. ターゲットDizinに移動
# TARGET_DIRが絶対Yolか相対Yolかを判定
if [[ "$TARGET_DIR" = /* ]]; then
    # 絶対Yol
    FULL_PATH="$TARGET_DIR"
else
    # 相対Yol
    FULL_PATH="$PROJECT_ROOT/$TARGET_DIR"
fi

./communication/agent_send.sh "$AGENT_ID" "cd $FULL_PATH"

# 3. 現在地をKontrol
./communication/agent_send.sh "$AGENT_ID" "pwd"

# 4. AjanBaşlatmaScriptをYürütme
# 注：AjanのカレントDizinにstart_agent_local.shを配置する必要がある
echo "📝 Creating local startup script..."
cat > "$FULL_PATH/start_agent_local.sh" << 'EOF'
#!/bin/bash
# AjanローカルBaşlatmaScript

set -e

# ProjeルートはOrtam değişkeniから取得
if [ -z "$VIBECODE_ROOT" ]; then
    echo "❌ Error: VIBECODE_ROOT not set"
    exit 1
fi

# AjanIDをArgümanから取得
AGENT_ID=$1
shift

# Ajanタイプを判定
determine_agent_type() {
    local agent_id=$1
    if [[ "$agent_id" =~ ^(PM|SE|PG|CD) ]]; then
        echo "polling"
    else
        echo "event-driven"
    fi
}

AGENT_TYPE=$(determine_agent_type "$AGENT_ID")
AGENT_DIR="$(pwd)"

echo "🔧 Setting up agent $AGENT_ID (type: $AGENT_TYPE)"

# HooksをAyar（VIBECODE_ENABLE_HOOKSがfalseでない限り有効）
if [ "${VIBECODE_ENABLE_HOOKS}" != "false" ]; then
    # CLI_HOOKS_MODEを取得（Ortam değişkeniから、デフォルトはauto）
    CLI_HOOKS_MODE="${CLI_HOOKS_MODE:-auto}"
    if [ -f "$VIBECODE_ROOT/hooks/setup_agent_hooks.sh" ]; then
        "$VIBECODE_ROOT/hooks/setup_agent_hooks.sh" "$AGENT_ID" "$AGENT_DIR" "$AGENT_TYPE" "$CLI_HOOKS_MODE"
    else
        echo "⚠️  Warning: setup_agent_hooks.sh not found"
    fi
fi

# working_dirをJSONLテーブルにKayıt
if command -v jq &> /dev/null; then
    TABLE_FILE="$VIBECODE_ROOT/Agent-shared/agent_and_pane_id_table.jsonl"
    if [ -f "$TABLE_FILE" ]; then
        echo "📝 Updating working_dir for $AGENT_ID"
        WORKING_DIR="${AGENT_DIR#$VIBECODE_ROOT/}"
        
        # 一時DosyaをKullanımして更新
        TEMP_FILE="$TABLE_FILE.tmp"
        while IFS= read -r line; do
            if [[ -z "$line" || "$line" =~ ^# ]]; then
                echo "$line"
            else
                updated_line=$(echo "$line" | jq -c --arg id "$AGENT_ID" --arg dir "$WORKING_DIR" '
                    if .agent_id == $id then
                        . + {working_dir: $dir, last_updated: (now | strftime("%Y-%m-%dT%H:%M:%SZ"))}
                    else
                        .
                    end
                ')
                echo "$updated_line"
            fi
        done < "$TABLE_FILE" > "$TEMP_FILE"
        mv "$TEMP_FILE" "$TABLE_FILE"
        echo "✅ Updated working_dir to: $WORKING_DIR"
    fi
fi

# PM/SE/PGAjanの場合、MCP（Desktop Commander）をAyar
if [[ "$AGENT_ID" =~ ^(PM|SE|PG) ]]; then
    echo "🔧 Setting up MCP for $AGENT_ID agent"
    claude mcp add desktop-commander -- npx -y @wonderwhy-er/desktop-commander
fi

# テレメトリAyarに基づいてClaudeBaşlatma
if [ "${VIBECODE_ENABLE_TELEMETRY}" = "false" ]; then
    echo "📊 Telemetry disabled - starting agent without telemetry"
    exec claude --dangerously-skip-permissions "$@"
else
    echo "📊 Telemetry enabled - starting agent with telemetry"
    exec "$VIBECODE_ROOT/telemetry/launch_claude_with_env.sh" "$AGENT_ID" "$@"
fi
EOF

chmod +x "$FULL_PATH/start_agent_local.sh"

# CLI_HOOKS_MODEの値をstart_agent_local.shに埋め込む（Ortam değişkeni依存を回避）
sed -i.bak "s|CLI_HOOKS_MODE=\"\\\${CLI_HOOKS_MODE:-auto}\"|CLI_HOOKS_MODE=\"$CLI_HOOKS_MODE\"|" "$FULL_PATH/start_agent_local.sh"
rm -f "$FULL_PATH/start_agent_local.sh.bak"

# 5. BaşlatmaScriptをYürütme
./communication/agent_send.sh "$AGENT_ID" "./start_agent_local.sh $AGENT_ID $ADDITIONAL_OPTIONS"

echo "✅ Agent $AGENT_ID startup initiated at $TARGET_DIR"
echo ""
echo "Note: The agent should now be starting with Claude Code."
echo "Check the tmux pane for the agent's status."