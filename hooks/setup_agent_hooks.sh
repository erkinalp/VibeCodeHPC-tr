#!/bin/bash
# VibeCodeHPC エージェント用hooks設定スクリプト
# PMが各エージェント起動時に実行

set -e

# 引数チェック
if [ $# -lt 3 ]; then
    echo "Usage: $0 <AGENT_ID> <AGENT_DIR> <AGENT_TYPE>"
    echo "Example: $0 PG1.1.1 /path/to/agent/dir event-driven"
    echo "AGENT_TYPE: polling or event-driven"
    exit 1
fi

AGENT_ID=$1
AGENT_DIR=$2
AGENT_TYPE=$3

# プロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$PROJECT_ROOT/hooks/templates"

echo "🔧 Setting up hooks for agent: $AGENT_ID (type: $AGENT_TYPE)"

# .claude/hooks ディレクトリ作成
mkdir -p "$AGENT_DIR/.claude/hooks"

# session_start.pyをコピー（全エージェント共通）
cp "$TEMPLATE_DIR/session_start.py" "$AGENT_DIR/.claude/hooks/"

# agent_id.txtを作成
echo "$AGENT_ID" > "$AGENT_DIR/.claude/hooks/agent_id.txt"

# エージェントタイプに応じたstop hookをコピー
# v0.4以降：PGもポーリング型に変更（全エージェントがポーリング型）
# v0.5: SOLOエージェント対応
if [ "$AGENT_ID" = "SOLO" ]; then
    cp "$TEMPLATE_DIR/stop_solo.py" "$AGENT_DIR/.claude/hooks/stop.py"
    # settings.jsonを作成（SOLOも同じ構造）
    cat > "$AGENT_DIR/.claude/settings.local.json" << EOF
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/stop.py"
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/session_start.py"
      }]
    }]
  }
}
EOF
    echo "✅ SOLO agent hooks configured"
elif [ "$AGENT_TYPE" = "polling" ] || [[ "$AGENT_ID" =~ ^PG ]]; then
    cp "$TEMPLATE_DIR/stop_polling_v2.py" "$AGENT_DIR/.claude/hooks/stop.py"
    # settings.jsonを作成（絶対パスを使用）
    cat > "$AGENT_DIR/.claude/settings.local.json" << EOF
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/stop.py"
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/session_start.py"
      }]
    }]
  }
}
EOF
    echo "✅ Polling agent hooks configured with absolute paths"
else
    cp "$TEMPLATE_DIR/stop_event.py" "$AGENT_DIR/.claude/hooks/stop.py"
    # settings.jsonを作成（絶対パスを使用）
    cat > "$AGENT_DIR/.claude/settings.local.json" << EOF
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/stop.py"
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/session_start.py"
      }]
    }]
  }
}
EOF
    echo "✅ Event-driven agent hooks configured with absolute paths"
fi

# 実行権限を付与
chmod +x "$AGENT_DIR/.claude/hooks/"*.py

# stop_count.txtを初期化（0から開始）
echo "0" > "$AGENT_DIR/.claude/hooks/stop_count.txt"

echo "✅ Hooks setup completed for $AGENT_ID at $AGENT_DIR"