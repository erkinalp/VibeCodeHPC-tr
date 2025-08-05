#!/bin/bash
# エージェント起動用ラッパースクリプト
# PMが使用：各エージェントを適切な場所に移動して起動
# 
# 環境変数 VIBECODE_ENABLE_TELEMETRY が false の場合はテレメトリなしで起動

if [ $# -lt 2 ]; then
    echo "Usage: $0 <AGENT_ID> <TARGET_DIR> [additional_options]"
    echo "Example: $0 PG1.1.1 /Flow/TypeII/single-node/intel2024/OpenMP"
    echo ""
    echo "Environment variables:"
    echo "  VIBECODE_ENABLE_TELEMETRY=false  # テレメトリを無効化"
    exit 1
fi

AGENT_ID=$1
TARGET_DIR=$2
shift 2

# スクリプトのディレクトリからプロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# エージェントタイプを判定
determine_agent_type() {
    local agent_id=$1
    # PM, SE, CI, CDはポーリング型
    if [[ "$agent_id" =~ ^(PM|SE|CI|CD) ]]; then
        echo "polling"
    else
        echo "event-driven"
    fi
}

AGENT_TYPE=$(determine_agent_type "$AGENT_ID")

# エージェントにコマンドを送信
echo "🚀 Starting agent $AGENT_ID (type: $AGENT_TYPE) at $TARGET_DIR"

# 1. プロジェクトルートを環境変数として設定
./communication/agent_send.sh "$AGENT_ID" "export VIBECODE_ROOT='$PROJECT_ROOT'"

# 2. ターゲットディレクトリに移動（通常のcd）
./communication/agent_send.sh "$AGENT_ID" "cd $PROJECT_ROOT$TARGET_DIR"

# 3. 現在地を確認
./communication/agent_send.sh "$AGENT_ID" "pwd"

# 4. Hooksを設定（VIBECODE_ENABLE_HOOKSがfalseでない限り有効）
if [ "${VIBECODE_ENABLE_HOOKS}" != "false" ]; then
    echo "🔧 Setting up hooks for $AGENT_ID"
    
    # フルパスのターゲットディレクトリを構築
    FULL_TARGET_DIR="$PROJECT_ROOT$TARGET_DIR"
    
    # setup_agent_hooks.shを実行
    if [ -f "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" ]; then
        "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" "$AGENT_ID" "$FULL_TARGET_DIR" "$AGENT_TYPE"
    else
        echo "⚠️  Warning: setup_agent_hooks.sh not found, skipping hooks setup"
    fi
fi

# 4.5. working_dirをJSONLテーブルに記録
if command -v jq &> /dev/null; then
    TABLE_FILE="$PROJECT_ROOT/Agent-shared/agent_and_pane_id_table.jsonl"
    if [ -f "$TABLE_FILE" ]; then
        echo "📝 Updating working_dir for $AGENT_ID"
        # TARGET_DIRから先頭の/を削除（relative_to()の出力と合わせるため）
        WORKING_DIR="${TARGET_DIR#/}"
        
        # 一時ファイルを使用して更新
        TEMP_FILE="$TABLE_FILE.tmp"
        while IFS= read -r line; do
            if [[ -z "$line" || "$line" =~ ^# ]]; then
                echo "$line"
            else
                # JSONとして解析して、該当エージェントIDの場合はworking_dirを更新
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
        
        # 一時ファイルを本体に置き換え
        mv "$TEMP_FILE" "$TABLE_FILE"
        echo "✅ Updated working_dir to: $WORKING_DIR"
    fi
else
    echo "⚠️  jq not found, skipping working_dir update"
fi

# 4.6. CIエージェントの場合、MCP（Desktop Commander）を設定
if [[ "$AGENT_ID" =~ ^CI ]]; then
    echo "🔧 Setting up MCP for CI agent"
    ./communication/agent_send.sh "$AGENT_ID" "claude mcp add desktop-commander -- npx -y @wonderwhy-er/desktop-commander"
fi

# 5. テレメトリ設定に基づいてClaude起動
if [ "${VIBECODE_ENABLE_TELEMETRY}" = "false" ]; then
    echo "📊 Telemetry disabled - starting agent without telemetry"
    # bash/zsh対応プロンプト設定
    ./communication/agent_send.sh "$AGENT_ID" "if [ -n \"\$ZSH_VERSION\" ]; then"
    ./communication/agent_send.sh "$AGENT_ID" "  export PROMPT=$'%{\033[1;33m%}(${AGENT_ID})%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '"
    ./communication/agent_send.sh "$AGENT_ID" "elif [ -n \"\$BASH_VERSION\" ]; then"
    ./communication/agent_send.sh "$AGENT_ID" "  export PS1='(\\[\\033[1;33m\\]${AGENT_ID}\\[\\033[0m\\]) \\[\\033[1;32m\\]\\w\\[\\033[0m\\]\\$ '"
    ./communication/agent_send.sh "$AGENT_ID" "fi"
    # Claude起動
    ./communication/agent_send.sh "$AGENT_ID" "claude --dangerously-skip-permissions $@"
    echo "✅ Agent $AGENT_ID started without telemetry at $TARGET_DIR"
else
    echo "📊 Telemetry enabled - starting agent with telemetry"
    # start_agent_with_telemetry.shを使用して起動
    ./communication/agent_send.sh "$AGENT_ID" "\$VIBECODE_ROOT/telemetry/start_agent_with_telemetry.sh ${AGENT_ID} $@"
    echo "✅ Agent $AGENT_ID started with telemetry at $TARGET_DIR"
fi