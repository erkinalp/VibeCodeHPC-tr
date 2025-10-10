#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "🚀 VibeCodeHPC Tek Aracı Modu Başlatılıyor"
echo "============================================"

TMUX_AVAILABLE=false
if command -v tmux &>/dev/null; then
    TMUX_AVAILABLE=true
    if [ -n "$TMUX_PANE" ]; then
        echo "✅ tmux ortamında çalışıyor: $TMUX_PANE"
    else
        echo "⚠️  tmux içinde çalışmıyor."
        echo "   Öneri: tmux attach-session -t Team1_PM"
    fi
else
    echo "⚠️  tmux kurulu değil. tmux olmadan çalışacak."
    echo "   tmux kurulumu önerilir. Ayrıntılar için README.md."
fi

if [ "${VIBECODE_ENABLE_HOOKS}" != "false" ]; then
    # CLI_HOOKS_MODE değerini al (varsayılan: auto)
    CLI_HOOKS_MODE="${CLI_HOOKS_MODE:-auto}"
    echo "🔧 Setting up hooks for SOLO agent..."
    echo "   CLI_HOOKS_MODE: $CLI_HOOKS_MODE"
    if [ -f "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" ]; then
        "$PROJECT_ROOT/hooks/setup_agent_hooks.sh" SOLO "$PROJECT_ROOT" polling "$CLI_HOOKS_MODE"
    else
        echo "⚠️  Warning: hooks setup script not found"
    fi
else
    echo "⚠️  Hooks disabled by VIBECODE_ENABLE_HOOKS=false"
fi

START_TIME_FILE="$PROJECT_ROOT/Agent-shared/project_start_time.txt"
if [ ! -f "$START_TIME_FILE" ] || [ ! -s "$START_TIME_FILE" ]; then
    echo "📅 Recording project start time..."
    mkdir -p "$PROJECT_ROOT/Agent-shared"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$START_TIME_FILE"
fi

# 3. agent_and_pane_id_table.jsonl içindeki SOLO kaydını güncelle
if command -v jq &> /dev/null; then
    TABLE_FILE="$PROJECT_ROOT/Agent-shared/agent_and_pane_id_table.jsonl"
    if [ -f "$TABLE_FILE" ]; then
        echo "📝 Updating working_dir for SOLO..."
        TEMP_FILE="$TABLE_FILE.tmp"
        while IFS= read -r line; do
            if [[ -z "$line" || "$line" =~ ^# ]]; then
                echo "$line"
            else
                updated_line=$(echo "$line" | jq -c '
                    if .agent_id == "SOLO" then
                        . + {working_dir: "", last_updated: (now | strftime("%Y-%m-%dT%H:%M:%SZ"))}
                    else
                        .
                    end
                ')
                echo "$updated_line"
            fi
        done < "$TABLE_FILE" > "$TEMP_FILE"
        mv "$TEMP_FILE" "$TABLE_FILE"
        echo "✅ Updated SOLO working_dir"
    fi
fi

# 4. stop_thresholds.json’a SOLO için eşik ekle (yoksa)
THRESHOLDS_FILE="$PROJECT_ROOT/Agent-shared/stop_thresholds.json"
if [ -f "$THRESHOLDS_FILE" ] && command -v jq &> /dev/null; then
    if ! jq '.thresholds | has("SOLO")' "$THRESHOLDS_FILE" | grep -q true; then
        echo "📝 Adding SOLO threshold to stop_thresholds.json..."
        TEMP_FILE="$THRESHOLDS_FILE.tmp"
        jq '.thresholds.SOLO = 100' "$THRESHOLDS_FILE" > "$TEMP_FILE"
        mv "$TEMP_FILE" "$THRESHOLDS_FILE"
        echo "✅ Added SOLO threshold (100 stops)"
    fi
fi

echo "🔧 Setting up MCP for SOLO agent..."
claude mcp add desktop-commander -- npx -y @wonderwhy-er/desktop-commander 2>/dev/null || {
    echo "⚠️  MCP yapılandırması atlandı (zaten ayarlı veya hata)"
}

# 6. Claude’u başlat
echo ""
echo "Başladıktan sonra, aşağıdaki istemi kopyalayıp yapıştırın:"
echo "================================================================"
cat << 'EOF'
VibeCodeHPC tek aracı modunda çalışacaksınız.
Tüm rolleri (PM/SE/PG/CD) tek başınıza üstlenip projeyi verimli şekilde ilerleteceksiniz.

[İlk Ayar]
Önce aşağıdaki dosyaları okuyun:
- CLAUDE.md (tüm aracılar için ortak kurallar)
- instructions/SOLO.md (tek mod için birleşik istem)
- requirement_definition.md (varsa)
- Agent-shared/project_start_time.txt (proje başlangıç zamanı)

[ToDo listesi ile rol yönetimi]
TodoWrite aracını etkin kullanın, her görevi rol etiketleriyle ([PM], [SE], [PG], [CD]) yönetin.

[Zaman yönetimi]
- Proje başlangıcından geçen süreyi düzenli kontrol edin
- requirement_definition.md’de süre sınırı varsa kesinlikle uyun
- Bütçe yönetimiyle birlikte zaman verimliliğine de odaklanın

[Verimli yürütme sırası]
1. [PM] Gereksinim tanımı ve ortam araştırması
2. [SE] Ortam kurulumu
3. [PG] Uygulama ve test (döngü)
4. [SE] İstatistik ve görselleştirme
5. [CD] GitHub senkronizasyonu (gerekirse)
6. [PM] Son rapor

agent_send.sh gerekli değil (iletişim hedefi yok).
Tüm işlemleri dahili olarak tamamlayın.

Projeyi başlatın.
EOF
echo "================================================================"
echo ""

if [ "${VIBECODE_ENABLE_TELEMETRY}" = "false" ]; then
    echo "📊 Telemetry disabled - starting SOLO without telemetry"
    exec claude --dangerously-skip-permissions "$@"
else
    echo "📊 Telemetry enabled - starting SOLO with telemetry"
    exec "$PROJECT_ROOT/telemetry/launch_claude_with_env.sh" SOLO "$@"
fi
