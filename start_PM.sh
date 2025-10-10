#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "🎯 VibeCodeHPC PM Başlatma Scripti"
echo "================================"

if [ "${VIBECODE_ENABLE_HOOKS}" != "false" ]; then
    # CLI_HOOKS_MODEを取得（デフォルト: auto）
    CLI_HOOKS_MODE="${CLI_HOOKS_MODE:-auto}"
    echo "🔧 Setting up hooks for PM..."
    echo "   CLI_HOOKS_MODE: $CLI_HOOKS_MODE"
    if [ -f "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" ]; then
        "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" PM "$PROJECT_ROOT" polling "$CLI_HOOKS_MODE"
    else
        echo "⚠️  Warning: hooks setup script not found"
    fi
else
    echo "⚠️  Hooks disabled by VIBECODE_ENABLE_HOOKS=false"
fi

# 1.5. TMUX_PANE ortam değişkenini kontrol et ve kaydet
echo "🔍 Checking TMUX environment..."
if [ -n "$TMUX_PANE" ]; then
    echo "  TMUX_PANE: $TMUX_PANE"
    # settings.local.jsonに環境変数を追加（Claude Codeに引き継がれない可能性への対策）
    if [ -f "$PROJECT_ROOT/.claude/settings.local.json" ]; then
        echo "  ⚠️  Note: Claude Code may not inherit TMUX_PANE environment variable"
    fi
else
    echo "  ⚠️  Warning: Not running in tmux pane"
fi

START_TIME_FILE="$PROJECT_ROOT/Agent-shared/project_start_time.txt"
if [ ! -f "$START_TIME_FILE" ] || [ ! -s "$START_TIME_FILE" ]; then
    echo "📅 Recording project start time..."
    mkdir -p "$PROJECT_ROOT/Agent-shared"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$START_TIME_FILE"
fi

if command -v jq &> /dev/null; then
    TABLE_FILE="$PROJECT_ROOT/Agent-shared/agent_and_pane_id_table.jsonl"
    if [ -f "$TABLE_FILE" ]; then
        echo "📝 Updating working_dir for PM..."
        TEMP_FILE="$TABLE_FILE.tmp"
        while IFS= read -r line; do
            if [[ -z "$line" || "$line" =~ ^# ]]; then
                echo "$line"
            else
                # JSONとして解析して、PMの場合はworking_dirを更新
                updated_line=$(echo "$line" | jq -c '
                    if .agent_id == "PM" then
                        . + {working_dir: "", last_updated: (now | strftime("%Y-%m-%dT%H:%M:%SZ"))}
                    else
                        .
                    end
                ')
                echo "$updated_line"
            fi
        done < "$TABLE_FILE" > "$TEMP_FILE"
        mv "$TEMP_FILE" "$TABLE_FILE"
        echo "✅ Updated PM working_dir"
    fi
fi

# 3. Claude’u başlat
echo ""
echo "Başladıktan sonra aşağıdaki istemi kopyalayıp yapıştırın:"
echo "================================================================"
cat << 'EOF'
Siz bir PM’siniz (Project Manager). VibeCodeHPC projesini başlatın.

Önce şu dosyaları okuyarak genel resmi anlayın:
- CLAUDE.md (tüm aracılar için ortak kurallar)
- instructions/PM.md (rolünüzün ayrıntıları)
- requirement_definition.md (proje gereksinimleri) — varsa
- Agent-shared/ altındaki tüm .md ve .txt dosyaları (.py, _template, _example hariç)

Özellikle önemli:
- max_agent_number.txt (kullanılabilir çalışan sayısı)
- agent_and_pane_id_table.jsonl (oturum yapısı ve aracı yönetimi)
- directory_pane_map.txt (aracı yerleşimi ve pencere/pane yönetimi)
- sota_management.md (SOTA yönetimi ve family kavramının önemi)

Hepsini okuduktan sonra mevcut ilgili tmux oturumlarını kullanarak projeyi başlatın. Yeni oturum oluşturmayın.
EOF
echo "================================================================"
echo ""

# テレメトリ設定に基づいてClaude起動
if [ "${VIBECODE_ENABLE_TELEMETRY}" = "false" ]; then
    echo "📊 Telemetry disabled - starting PM without telemetry"
    exec claude --dangerously-skip-permissions "$@"
else
    echo "📊 Telemetry enabled - starting PM with telemetry"
    exec "$PROJECT_ROOT/telemetry/launch_claude_with_env.sh" PM "$@"
fi
