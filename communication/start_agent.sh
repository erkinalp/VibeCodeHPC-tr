#!/bin/bash

if [ $# -lt 2 ]; then
    echo "Usage: $0 <AGENT_ID> <TARGET_DIR> [additional_options]"
    echo "Example: $0 PG1.1.1 /Flow/TypeII/single-node/intel2024/OpenMP"
    echo ""
    echo "Environment variables:"
    echo "  VIBECODE_ENABLE_TELEMETRY=false  # Telemetriyi devre dışı bırak"
    echo "  VIBECODE_ENABLE_HOOKS=false      # kancaları devre dışı bırak (önerilmez)"
    exit 1
fi

AGENT_ID=$1
TARGET_DIR=$2
shift 2
ADDITIONAL_OPTIONS="$@"

PROJECT_ROOT="$(pwd)"

# agent_and_pane_id_table.jsonl içinde aracı ID’sini kontrol et
TABLE_FILE="$PROJECT_ROOT/Agent-shared/agent_and_pane_id_table.jsonl"
if [ -f "$TABLE_FILE" ]; then
    # AGENT_ID 'beklemede' ile başlıyor mu kontrol et
    if [[ "$AGENT_ID" =~ ^beklemede ]]; then
        echo "❌ Hata: Aracı ID'si 'beklemede' olarak kalmış"
        echo "   Önce agent_and_pane_id_table.jsonl içindeki agent_id'yi doğru kimlik ile güncelleyin (ör: PG1.1.3)"
        echo ""
        echo "   Örnek: 'beklemede3' → 'PG1.1.3'"
        echo ""
        echo "   Sonrasında bu komutu doğru kimlikle çalıştırın:"
        echo "   ./communication/start_agent.sh PG1.1.3 $TARGET_DIR"
        exit 1
    fi
    
    if command -v jq &> /dev/null; then
        if ! grep -q "\"agent_id\":[[:space:]]*\"$AGENT_ID\"" "$TABLE_FILE"; then
            echo "⚠️  Uyarı: agent_and_pane_id_table.jsonl içinde $AGENT_ID bulunamadı"
            echo "   Çalıştırmadan önce tabloya aracı kimliğini eklemenizi öneririz"
        fi
    fi
fi

echo "🚀 Starting agent $AGENT_ID at $TARGET_DIR"

./communication/agent_send.sh "$AGENT_ID" "export VIBECODE_ROOT='$PROJECT_ROOT'"

# CLI_HOOKS_MODE’u ortam değişkeni olarak ayarla (ayarlı değilse auto)
CLI_HOOKS_MODE="${CLI_HOOKS_MODE:-auto}"
./communication/agent_send.sh "$AGENT_ID" "export CLI_HOOKS_MODE='$CLI_HOOKS_MODE'"

# TARGET_DIR mutlak mı göreli mi kontrol et
if [[ "$TARGET_DIR" = /* ]]; then
    FULL_PATH="$TARGET_DIR"
else
    FULL_PATH="$PROJECT_ROOT/$TARGET_DIR"
fi

./communication/agent_send.sh "$AGENT_ID" "cd $FULL_PATH"

./communication/agent_send.sh "$AGENT_ID" "pwd"

echo "📝 Creating local startup script..."
cat > "$FULL_PATH/start_agent_local.sh" << 'EOF'
#!/bin/bash

set -e

if [ -z "$VIBECODE_ROOT" ]; then
    echo "❌ Error: VIBECODE_ROOT not set"
    exit 1
fi

AGENT_ID=$1
shift

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

if [ "${VIBECODE_ENABLE_HOOKS}" != "false" ]; then
    # CLI_HOOKS_MODE’u al (ortam değişkeninden, varsayılan auto)
    CLI_HOOKS_MODE="${CLI_HOOKS_MODE:-auto}"
    if [ -f "$VIBECODE_ROOT/hooks/setup_agent_hooks.sh" ]; then
        "$VIBECODE_ROOT/hooks/setup_agent_hooks.sh" "$AGENT_ID" "$AGENT_DIR" "$AGENT_TYPE" "$CLI_HOOKS_MODE"
    else
        echo "⚠️  Warning: setup_agent_hooks.sh not found"
    fi
fi

# working_dir değerini JSONL tabloda kaydet
if command -v jq &> /dev/null; then
    TABLE_FILE="$VIBECODE_ROOT/Agent-shared/agent_and_pane_id_table.jsonl"
    if [ -f "$TABLE_FILE" ]; then
        echo "📝 Updating working_dir for $AGENT_ID"
        WORKING_DIR="${AGENT_DIR#$VIBECODE_ROOT/}"
        
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

# PM/SE/PG ajanları için MCP (Desktop Commander) kurulumu
if [[ "$AGENT_ID" =~ ^(PM|SE|PG) ]]; then
    echo "🔧 Setting up MCP for $AGENT_ID agent"
    claude mcp add desktop-commander -- npx -y @wonderwhy-er/desktop-commander
fi

if [ "${VIBECODE_ENABLE_TELEMETRY}" = "false" ]; then
    echo "📊 Telemetry disabled - starting agent without telemetry"
    exec claude --dangerously-skip-permissions "$@"
else
    echo "📊 Telemetry enabled - starting agent with telemetry"
    exec "$VIBECODE_ROOT/telemetry/launch_claude_with_env.sh" "$AGENT_ID" "$@"
fi
EOF

chmod +x "$FULL_PATH/start_agent_local.sh"

# CLI_HOOKS_MODE değerini start_agent_local.sh içine göm (ortam değişkeni bağımlılığını azalt)
sed -i.bak "s|CLI_HOOKS_MODE=\"\\\${CLI_HOOKS_MODE:-auto}\"|CLI_HOOKS_MODE=\"$CLI_HOOKS_MODE\"|" "$FULL_PATH/start_agent_local.sh"
rm -f "$FULL_PATH/start_agent_local.sh.bak"

./communication/agent_send.sh "$AGENT_ID" "./start_agent_local.sh $AGENT_ID $ADDITIONAL_OPTIONS"

echo "✅ Agent $AGENT_ID startup initiated at $TARGET_DIR"
echo ""
echo "Note: The agent should now be starting with Claude Code."
echo "Check the tmux pane for the agent's status."
