#!/bin/bash
# VibeCodeHPC ajanları için hooks ayar betiği

set -e

if [ $# -lt 3 ]; then
    echo "Usage: $0 <AGENT_ID> <AGENT_DIR> <AGENT_TYPE> [CLI_HOOKS_MODE]"
    echo "Example: $0 PG1.1.1 /path/to/agent/dir polling custom"
    echo "AGENT_TYPE: polling or event-driven"
    echo "CLI_HOOKS_MODE: auto (default), custom, or hybrid"
    exit 1
fi

AGENT_ID=$1
AGENT_DIR=$2
AGENT_TYPE=$3
CLI_HOOKS_MODE="${4:-auto}"  # 4. argümandan alınır, belirtilmezse auto

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$PROJECT_ROOT/hooks/templates"

if [ -f "$SCRIPT_DIR/.hooks_version" ]; then
    HOOKS_VERSION=$(cat "$SCRIPT_DIR/.hooks_version")
else
    HOOKS_VERSION="v3"  # Varsayılan v3
fi

echo "🔧 Setting up hooks for agent: $AGENT_ID (type: $AGENT_TYPE, version: $HOOKS_VERSION)"
echo "   CLI_HOOKS_MODE: $CLI_HOOKS_MODE"

# .claude/hooks dizinini oluştur
mkdir -p "$AGENT_DIR/.claude/hooks"

# session_start.py’yi kopyala (tüm ajanlar için ortak)
cp "$TEMPLATE_DIR/session_start.py" "$AGENT_DIR/.claude/hooks/"

# post_tool_ssh_handler.py’yi kopyala (PostToolUse SSH/SFTP desteği)
cp "$TEMPLATE_DIR/post_tool_ssh_handler.py" "$AGENT_DIR/.claude/hooks/"

# agent_id.txt oluştur
echo "$AGENT_ID" > "$AGENT_DIR/.claude/hooks/agent_id.txt"

# v0.5: SOLO ajanı da v3 kullanır (auto_tuning_config.json kullanımı)

# CLI_HOOKS_MODE=custom ise hooks bölümü boş bırakılır
if [ "$CLI_HOOKS_MODE" = "custom" ]; then
    echo "   Custom hooks mode: hooks section will be empty"
    if [ "$AGENT_TYPE" = "polling" ] || [[ "$AGENT_ID" =~ ^PG ]] || [ "$AGENT_ID" = "SOLO" ]; then
        cp "$TEMPLATE_DIR/stop_polling_v3.py" "$AGENT_DIR/.claude/hooks/stop.py"
    else
        cp "$TEMPLATE_DIR/stop_event.py" "$AGENT_DIR/.claude/hooks/stop.py"
    fi

    # settings.local.json boş hooks ile oluşturulur (Claude başlamadan önce mevcut ayar yok)
    cat > "$AGENT_DIR/.claude/settings.local.json" << EOF
{
  "hooks": {}
}
EOF
    echo "✅ Custom hooks mode configured (hooks will be called by state monitor)"

elif [ "$AGENT_ID" = "SOLO" ]; then
    cp "$TEMPLATE_DIR/stop_polling_v3.py" "$AGENT_DIR/.claude/hooks/stop.py"
    # settings.local.json oluştur (SOLO için de aynı yapı)
    cat > "$AGENT_DIR/.claude/settings.local.json" << EOF
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "mcp__desktop-commander__start_process|Bash",
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/post_tool_ssh_handler.py"
      }]
    }],
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
    echo "✅ SOLO agent hooks configured (using v3 with SOLO probabilities)"
elif [ "$AGENT_TYPE" = "polling" ] || [[ "$AGENT_ID" =~ ^PG ]]; then
    if [ "$HOOKS_VERSION" = "v2" ]; then
        cp "$TEMPLATE_DIR/stop_polling_v2.py" "$AGENT_DIR/.claude/hooks/stop.py"
    elif [ "$HOOKS_VERSION" = "v3" ]; then
        cp "$TEMPLATE_DIR/stop_polling_v3.py" "$AGENT_DIR/.claude/hooks/stop.py"
    else
        echo "⚠️ Unknown hooks version '$HOOKS_VERSION', using v3"
        cp "$TEMPLATE_DIR/stop_polling_v3.py" "$AGENT_DIR/.claude/hooks/stop.py"
    fi
    # settings.local.json oluştur (mutlak yollar kullanılır)
    cat > "$AGENT_DIR/.claude/settings.local.json" << EOF
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "mcp__desktop-commander__start_process|Bash",
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/post_tool_ssh_handler.py"
      }]
    }],
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
    # settings.local.json oluştur (mutlak yollar kullanılır)
    cat > "$AGENT_DIR/.claude/settings.local.json" << EOF
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "mcp__desktop-commander__start_process|Bash",
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/post_tool_ssh_handler.py"
      }]
    }],
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

chmod +x "$AGENT_DIR/.claude/hooks/"*.py

# stop_count.txt’i başlat (0’dan başlar)
echo "0" > "$AGENT_DIR/.claude/hooks/stop_count.txt"

echo "✅ Hooks setup completed for $AGENT_ID at $AGENT_DIR"
