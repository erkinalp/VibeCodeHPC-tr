#!/bin/bash
# エージェント起動用ラッパースクリプト
# PMが使用：各エージェントを適切な場所に移動してテレメトリ付きで起動

if [ $# -lt 2 ]; then
    echo "Usage: $0 <AGENT_ID> <TARGET_DIR> [additional_options]"
    echo "Example: $0 PG1.1.1 /Flow/TypeII/single-node/intel2024/OpenMP"
    exit 1
fi

AGENT_ID=$1
TARGET_DIR=$2
shift 2

# スクリプトのディレクトリからプロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# エージェントにコマンドを送信
echo "🚀 Starting agent $AGENT_ID at $TARGET_DIR"

# 1. プロジェクトルートを環境変数として設定
./communication/agent-send.sh "$AGENT_ID" "export OPENCODEAT_ROOT='$PROJECT_ROOT'"

# 2. ターゲットディレクトリに移動
./communication/agent-send.sh "$AGENT_ID" "!cd $PROJECT_ROOT$TARGET_DIR"

# 3. 現在地を確認
./communication/agent-send.sh "$AGENT_ID" "pwd"

# 4. テレメトリ付きでClaude起動
./communication/agent-send.sh "$AGENT_ID" "\$OPENCODEAT_ROOT/telemetry/start_agent_with_telemetry.sh $AGENT_ID $@"

echo "✅ Agent $AGENT_ID started with telemetry at $TARGET_DIR"