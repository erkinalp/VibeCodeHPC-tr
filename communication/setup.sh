#!/bin/bash

# 🧬 VibeCodeHPC Multi-Agent HPC Environment Setup
# Dynamic tmux session creation for user-specified agent count

set -e  # Hata durumunda dur

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# グローバル変数
PROJECT_NAME=""  # Kullanıcının belirleyeceği proje adı
USE_DEFAULT_NAMES=true  # Varsayılan ad kullanım bayrağı
DRY_RUN=false  # dry-run bayrağı
HOOKS_VERSION="v3"  # hooks sürümü (varsayılan v3)
PERIODIC_ENTER_INTERVAL=60  # Periyodik Enter aralığı (saniye), 0=kapalı

# Varsayılan oturum adları
DEFAULT_PM_SESSION="Team1_PM"
DEFAULT_WORKER_SESSION="Team1_Workers1"
DEFAULT_WORKER_SESSION_PREFIX="Team1_Workers"  # 13+ durumları için

PM_SESSION=""
WORKER_SESSION=""
WORKER_SESSION_PREFIX=""

log_info() {
    echo -e "\033[1;32m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;34m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

show_usage() {
    cat << EOF
🧬 VibeCodeHPC çok aracılı YBH (yüksek başarımlı hesaplama) ortam kurulumu

Kullanım:
  $0 [işçi sayısı (PM hariç)] [Seçenekler]

Parametreler:
  İşçi sayısı    : PM dışındaki ajanların toplamı (en az: 3)
  
Seçenekler:
  --project <ad>         : Proje adı (ör: GEMM, MatMul)
  --hooks <v2|v3>        : hooks sürümü (varsayılan: v3)
  --periodic-enter <sn>  : Periyodik Enter aralığı (varsayılan: 60 sn, 0=kapalı)
  --clean-only           : Sadece mevcut oturumları temizle
  --dry-run              : Gerçek kurulum yapmadan planı göster
  --help                 : Bu yardımı göster

Örnek:
  $0 11                    # Varsayılan adlar (Team1_PM, Team1_Workers1)
  $0 11 --project GEMM     # Proje adı (GEMM_PM, GEMM_Workers1)
  $0 11 --hooks v2         # hooks v2 kullan
  $0 --clean-only          # Sadece temizlik
  $0 --dry-run 11          # 11 işçili yapı planını göster

Oturum adlandırma kuralları:
  Varsayılan: Team1_PM, Team1_Workers1, Team1_Workers2...
  Proje adıyla: <ProjectName>_PM, <ProjectName>_Workers1...

Örnek yapılandırmalar (nihai yerleşimi PM belirler):
  2 kişi: SE(1) + PG(1) [en küçük yapı]
  6 kişi: SE(2) + PG(3) + CD(1)
  8 kişi: SE(2) + PG(5) + CD(1)
  11 kişi: SE(2) + PG(8) + CD(1)
  15 kişi: SE(3) + PG(11) + CD(1)
EOF
}

calculate_agent_distribution() {
    local total=$1  # PM hariç sayı
    
    if [ $total -lt 2 ]; then
        log_error "Ajan sayısı çok az. En az 2 ajan (PM hariç) gerekir."
        return 1
    fi
    
    local cd_count=0
    if [ $total -ne 2 ]; then
        cd_count=1
    fi
    
    local remaining=$((total - cd_count))
    
    local se_count
    if [ $total -eq 2 ]; then
        se_count=1
    elif [ $total -le 12 ]; then
        se_count=2
    else
        se_count=3
    fi
    
    local pg_count=$((remaining - se_count))
    
    echo "$se_count $pg_count $cd_count"
}

generate_agent_names() {
    local se_count=$1
    local pg_count=$2
    local cd_count=$3
    
    local agents=()
    
    # SE
    for ((i=1; i<=se_count; i++)); do
        agents+=("SE${i}")
    done
    
    # PG（階層的な番号付け）
    # SEが1人の場合: PG1.1, PG1.2, ...
    # SEが2人の場合: SE1配下→PG1.1, PG1.2, ..., SE2配下→PG2.1, PG2.2, ...
    local pg_idx=1
    if [ $se_count -eq 1 ]; then
        # 全てのPGをSE1配下に
        for ((p=1; p<=pg_count; p++)); do
            agents+=("PG1.$((p))")
        done
    else
        # PGを各SEに均等配分
        local pg_per_se=$(( (pg_count + se_count - 1) / se_count ))
        for ((s=1; s<=se_count; s++)); do
            for ((p=1; p<=pg_per_se && pg_idx<=pg_count; p++)); do
                agents+=("PG${s}.$((p))")
                pg_idx=$((pg_idx + 1))
            done
        done
    fi
    
    # CD
    agents+=("CD")
    
    echo "${agents[@]}"
}

# セッション名の決定
determine_session_names() {
    if [ "$USE_DEFAULT_NAMES" = true ]; then
        PM_SESSION="$DEFAULT_PM_SESSION"
        WORKER_SESSION="$DEFAULT_WORKER_SESSION"
        WORKER_SESSION_PREFIX="$DEFAULT_WORKER_SESSION_PREFIX"
    else
        PM_SESSION="${PROJECT_NAME}_PM"
        WORKER_SESSION="${PROJECT_NAME}_Workers1"
        WORKER_SESSION_PREFIX="${PROJECT_NAME}_Workers"
    fi
}

# セッション名の衝突チェック
check_session_conflicts() {
    local conflicts=false
    
    log_info "🔍 Oturum adlarının çakışması kontrol ediliyor..."
    
    # PMセッションのチェック
    if tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        log_error "❌ '$PM_SESSION' oturumu zaten mevcut"
        conflicts=true
    fi
    
    # ワーカーセッションのチェック
    if tmux has-session -t "$WORKER_SESSION" 2>/dev/null; then
        log_error "❌ '$WORKER_SESSION' oturumu zaten mevcut"
        conflicts=true
    fi
    
    if [ "$conflicts" = true ]; then
        echo ""
        echo "Mevcut oturumlar:"
        tmux list-sessions 2>/dev/null || echo "Oturum yok"
        echo ""
        echo "Çözüm yolları:"
        echo "1. Başka bir proje adı verin: $0 $1 --project &lt;yeni_ad&gt;"
        echo "2. Mevcut oturumu silin: tmux kill-session -t $PM_SESSION"
        echo "3. --clean-only ile eski oturumları temizleyin"
        return 1
    fi
    
    log_success "✅ Oturum adı çakışması yok"
    return 0
}

# セッション重複チェックとリネーム
handle_existing_sessions() {
    log_info "🔍 既存セッションの確認と処理..."
    
    # ディレクトリ準備
    mkdir -p ./Agent-shared
    mkdir -p ./communication/logs
    mkdir -p ./tmp
    rm -f ./tmp/agent*_done.txt 2>/dev/null
    
    sleep 0.5
    log_success "✅ Oturum hazırlığı tamam"
}

# PMセッション作成
create_pm_session() {
    log_info "📺 PM oturumu oluşturuluyor: $PM_SESSION"
    
    # 新しいPMセッション作成
    tmux new-session -d -s "$PM_SESSION" -n "project-manager"
    
    # セッションが作成されたか確認
    if ! tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        log_error "${PM_SESSION} oluşturulamadı"
        log_info "Mevcut oturumlar:"
        tmux list-sessions || echo "Oturum yok"
        return 1
    fi
    
    tmux send-keys -t "${PM_SESSION}:project-manager" "cd $PROJECT_ROOT" C-m

    # CLI_HOOKS_MODE環境変数を設定（親シェルから継承または auto）
    tmux send-keys -t "${PM_SESSION}:project-manager" "export CLI_HOOKS_MODE='${CLI_HOOKS_MODE:-auto}'" C-m

    # bash/zsh対応プロンプト設定
    tmux send-keys -t "${PM_SESSION}:project-manager" "if [ -n \"\$ZSH_VERSION\" ]; then" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "  export PROMPT=$'%{\033[1;35m%}(PM)%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "elif [ -n \"\$BASH_VERSION\" ]; then" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "  export PS1='(\[\033[1;35m\]PM\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "fi" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "clear" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo '=== PM (Proje Yöneticisi) Ajanı ==='" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo 'VibeCodeHPC HPC optimizasyon sistemi'" C-m
    if [ -n "$PROJECT_NAME" ] && [ "$USE_DEFAULT_NAMES" = false ]; then
        tmux send-keys -t "${PM_SESSION}:project-manager" "echo 'Proje: ${PROJECT_NAME}'" C-m
    fi
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo 'Rol: Proje yönetimi ve gereksinim tanımı'" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo ''" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo 'Ajan başlatma komutu:'" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo './start_PM.sh'" C-m
    
    log_success "✅ PM oturumu oluşturuldu"
}

# 状態表示pane更新関数生成
generate_status_display_script() {
    local agents=($1)
    local script_file="./tmp/update_status_display.sh"
    
    cat > "$script_file" << 'EOF'
#!/bin/bash
# 状態表示更新スクリプト

while true; do
    clear
    echo "[VibeCodeHPC Ajan Yerleşim Şeması]"
    echo "================================"
    
    # TODO: 実際の配置に基づいて動的に生成
    
    sleep 5
done
EOF
    
    chmod +x "$script_file"
}

# 単一ワーカーセッション作成（12ペインまで）
create_single_worker_session() {
    local session_name=$1
    local start_pane=$2
    local end_pane=$3
    local panes_in_session=$((end_pane - start_pane + 1))
    
    log_info "📺 ワーカーセッション作成: $session_name (${panes_in_session}ペイン)..."
    
    # 固定レイアウト計算
    local cols rows
    if [ $panes_in_session -le 4 ]; then
        cols=2; rows=2
    elif [ $panes_in_session -le 9 ]; then
        cols=3; rows=3
    elif [ $panes_in_session -le 12 ]; then
        cols=4; rows=3  # 4列x3行（標準設定）
    elif [ $panes_in_session -le 16 ]; then
        cols=4; rows=4
    else
        cols=5; rows=4
    fi
    
    log_info "グリッド構成: ${cols}列 x ${rows}行"
    
    # セッションを作成
    tmux new-session -d -s "$session_name" -n "hpc-agents"
    
    # セッションが作成されたか確認
    if ! tmux has-session -t "$session_name" 2>/dev/null; then
        log_error "${session_name}セッションの作成に失敗しました"
        return 1
    fi
    
    sleep 1
    
    # グリッド作成（エラーハンドリング付き）
    local pane_count=1
    local creation_failed=false
    
    # 最初の列を作成
    for ((j=1; j < rows && pane_count < panes_in_session; j++)); do
        if ! tmux split-window -v -t "${session_name}:hpc-agents" 2>&1 | grep -q "no space for new pane"; then
            ((pane_count++))
        else
            log_error "⚠️ ペイン作成失敗: no space for new pane (ペイン $pane_count/$panes_in_session)"
            creation_failed=true
            break
        fi
    done
    
    # 残りの列を作成（最初の列で失敗していない場合のみ）
    if [ "$creation_failed" = false ]; then
        for ((i=1; i < cols && pane_count < panes_in_session; i++)); do
            tmux select-pane -t "${session_name}:hpc-agents.0"
            if ! tmux split-window -h -t "${session_name}:hpc-agents" 2>&1 | grep -q "no space for new pane"; then
                ((pane_count++))
            else
                log_error "⚠️ ペイン作成失敗: no space for new pane (ペイン $pane_count/$panes_in_session)"
                creation_failed=true
                break
            fi
            
            if [ "$creation_failed" = false ]; then
                for ((j=1; j < rows && pane_count < panes_in_session; j++)); do
                    if ! tmux split-window -v -t "${session_name}:hpc-agents" 2>&1 | grep -q "no space for new pane"; then
                        ((pane_count++))
                    else
                        log_error "⚠️ ペイン作成失敗: no space for new pane (ペイン $pane_count/$panes_in_session)"
                        creation_failed=true
                        break
                    fi
                done
            fi
        done
    fi
    
    # ペイン作成が失敗した場合、作成できたペイン数を返す
    if [ "$creation_failed" = true ]; then
        log_error "❌ 要求された ${panes_in_session} ペインのうち、${pane_count} ペインのみ作成可能"
        # セッションを削除して失敗を返す
        tmux kill-session -t "$session_name" 2>/dev/null
        return 1
    fi
    
    # レイアウト調整
    tmux select-layout -t "${session_name}:hpc-agents" tiled
    
    # 全ペインの初期化
    local pane_indices=($(tmux list-panes -t "${session_name}:hpc-agents" -F "#{pane_index}"))
    
    for i in "${!pane_indices[@]}"; do
        local pane_index="${pane_indices[$i]}"
        local pane_target="${session_name}:hpc-agents.${pane_index}"
        
        tmux send-keys -t "$pane_target" "cd $PROJECT_ROOT" C-m

        # OpenTelemetry環境変数を設定（全ペイン共通）
        tmux send-keys -t "$pane_target" "export CLAUDE_CODE_ENABLE_TELEMETRY=1" C-m
        tmux send-keys -t "$pane_target" "export OTEL_METRICS_EXPORTER=otlp" C-m
        tmux send-keys -t "$pane_target" "export OTEL_METRIC_EXPORT_INTERVAL=10000" C-m
        tmux send-keys -t "$pane_target" "export OTEL_LOGS_EXPORTER=otlp" C-m
        tmux send-keys -t "$pane_target" "export OTEL_LOG_USER_PROMPTS=0" C-m
        tmux send-keys -t "$pane_target" "export OTEL_EXPORTER_OTLP_PROTOCOL=grpc" C-m
        tmux send-keys -t "$pane_target" "export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317" C-m

        # CLI_HOOKS_MODE環境変数を設定（親シェルから継承または auto）
        tmux send-keys -t "$pane_target" "export CLI_HOOKS_MODE='${CLI_HOOKS_MODE:-auto}'" C-m

        # 全ペインをワーカー用に設定
        local global_pane_num=$((start_pane + i))
        if false; then  # 旧コード（保守用）
            # 旧コード
            tmux select-pane -t "$pane_target" -T "STATUS"
            # bash/zsh対応プロンプト設定
            tmux send-keys -t "$pane_target" "if [ -n \"\$ZSH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PROMPT=$'%{\033[1;37m%}(STATUS)%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '" C-m
            tmux send-keys -t "$pane_target" "elif [ -n \"\$BASH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PS1='(\[\033[1;37m\]STATUS\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
            tmux send-keys -t "$pane_target" "fi" C-m
            tmux send-keys -t "$pane_target" "clear" C-m
            tmux send-keys -t "$pane_target" "echo '[VibeCodeHPC エージェント配置状態]'" C-m
            tmux send-keys -t "$pane_target" "echo '================================'" C-m
            tmux send-keys -t "$pane_target" "echo 'PMがエージェントを配置中...'" C-m
            tmux send-keys -t "$pane_target" "echo ''" C-m
            # グローバル変数を参照（create_worker_sessionsで設定）
            tmux send-keys -t "$pane_target" "echo 'ワーカー数: $GLOBAL_TOTAL_WORKERS'" C-m
            tmux send-keys -t "$pane_target" "echo 'directory_pane_map.md を参照してください'" C-m
        else
            # その他のペインはエージェント配置待ち
            local pane_number=$global_pane_num
            tmux select-pane -t "$pane_target" -T "Pane${pane_number}"
            
            # エージェント用のOTEL_RESOURCE_ATTRIBUTES準備（後でagent_idが決まったら更新）
            tmux send-keys -t "$pane_target" "export TMUX_PANE_ID='${pane_index}'" C-m
            tmux send-keys -t "$pane_target" "export OTEL_RESOURCE_ATTRIBUTES=\"tmux_pane=\${TMUX_PANE},pane_index=${pane_index}\"" C-m
            
            # bash/zsh対応プロンプト設定
            tmux send-keys -t "$pane_target" "if [ -n \"\$ZSH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PROMPT=$'%{\033[1;90m%}(待機中${pane_number})%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '" C-m
            tmux send-keys -t "$pane_target" "elif [ -n \"\$BASH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PS1='(\[\033[1;90m\]待機中${pane_number}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
            tmux send-keys -t "$pane_target" "fi" C-m
            tmux send-keys -t "$pane_target" "clear" C-m
            tmux send-keys -t "$pane_target" "echo '=== エージェント配置待ち (Pane ${pane_number}) ==='" C-m
            tmux send-keys -t "$pane_target" "echo ''" C-m
            tmux send-keys -t "$pane_target" "echo 'PMがdirectory_pane_map.mdで配置を決定します'" C-m
            tmux send-keys -t "$pane_target" "echo 'その後、エージェントが起動されます'" C-m
            tmux send-keys -t "$pane_target" "echo ''" C-m
            tmux send-keys -t "$pane_target" "echo '📊 OpenTelemetryが有効化されています'" C-m
            tmux send-keys -t "$pane_target" "echo '   OTLP エンドポイント: http://localhost:4317'" C-m
        fi
    done
    
    log_success "✅ ワーカーセッション作成完了: $session_name"
    return 0
}

# 複数ワーカーセッション作成（メイン関数）
create_worker_sessions() {
    local total_panes=$1  # ユーザ入力数 + 1 (STATUS用)
    
    # グローバル変数として総ワーカー数を記録
    GLOBAL_TOTAL_WORKERS=$((total_panes - 1))
    
    # まず単一セッションで試行
    log_info "🔧 Tek oturumda oluşturma denemesi yapılıyor..."
    if create_single_worker_session "$WORKER_SESSION" 0 $((total_panes - 1)); then
        log_success "✅ 単一セッションで作成成功"
        return 0
    fi
    
    # 単一セッションで失敗した場合、自動的に複数セッションに分割
    log_info "📦 'no space for new pane' hatası tespit edildi. Otomatik olarak birden çok oturuma bölünüyor"
    
    # より小さいペイン数で再試行
    local max_panes_per_session=12
    local test_panes=12
    
    # 実際に作成可能な最大ペイン数を探る（12から順に減らして試行）
    while [ $test_panes -ge 4 ]; do
        log_info "🔍 ${test_panes} panel ile test..."
        local test_session="${WORKER_SESSION_PREFIX}_test"
        
        # テストセッション作成
        tmux new-session -d -s "$test_session" -n "test" 2>/dev/null
        
        local test_success=true
        local pane_count=1
        
        # レイアウトテスト（4x3を基準に）
        local cols=4
        local rows=3
        if [ $test_panes -le 9 ]; then
            cols=3; rows=3
        elif [ $test_panes -le 6 ]; then
            cols=3; rows=2
        elif [ $test_panes -le 4 ]; then
            cols=2; rows=2
        fi
        
        # ペイン作成テスト
        for ((j=1; j < rows && pane_count < test_panes; j++)); do
            if tmux split-window -v -t "${test_session}:test" 2>&1 | grep -q "no space for new pane"; then
                test_success=false
                break
            fi
            ((pane_count++))
        done
        
        if [ "$test_success" = true ]; then
            for ((i=1; i < cols && pane_count < test_panes && test_success; i++)); do
                tmux select-pane -t "${test_session}:test.0" 2>/dev/null
                if tmux split-window -h -t "${test_session}:test" 2>&1 | grep -q "no space for new pane"; then
                    test_success=false
                    break
                fi
                ((pane_count++))
                
                for ((j=1; j < rows && pane_count < test_panes; j++)); do
                    if tmux split-window -v -t "${test_session}:test" 2>&1 | grep -q "no space for new pane"; then
                        test_success=false
                        break
                    fi
                    ((pane_count++))
                done
            done
        fi
        
        # テストセッション削除
        tmux kill-session -t "$test_session" 2>/dev/null
        
        if [ "$test_success" = true ]; then
            max_panes_per_session=$test_panes
            log_success "✅ Oturum başına en fazla ${max_panes_per_session} panel oluşturulabilir"
            break
        fi
        
        # 次の試行は3ペイン減らす
        test_panes=$((test_panes - 3))
    done
    
    # 複数セッションに分割して作成
    log_info "📦 ${max_panes_per_session}ペインごとに分割して作成します"
    
    local session_num=1
    local start_pane=0
    local remaining_panes=$total_panes
    local creation_success=true
    
    while [ $remaining_panes -gt 0 ]; do
        local panes_in_session
        if [ $remaining_panes -gt $max_panes_per_session ]; then
            panes_in_session=$max_panes_per_session
        else
            panes_in_session=$remaining_panes
        fi
        
        local session_name="${WORKER_SESSION_PREFIX}${session_num}"
        local end_pane=$((start_pane + panes_in_session - 1))
        
        if ! create_single_worker_session "$session_name" $start_pane $end_pane; then
            log_error "❌ ${session_name} oturumunun oluşturulması başarısız"
            creation_success=false
            break
        fi
        
        start_pane=$((start_pane + panes_in_session))
        remaining_panes=$((remaining_panes - panes_in_session))
        session_num=$((session_num + 1))
    done
    
    if [ "$creation_success" = true ]; then
        log_success "✅ Tüm işçi oturumları oluşturuldu (toplam: $((session_num - 1)) oturum)"
        return 0
    else
        return 1
    fi
}

# agent_and_pane_id_table生成（初期状態、複数セッション対応）
generate_agent_pane_table() {
    local total_panes=$1
    
    local jsonl_table_file="./Agent-shared/agent_and_pane_id_table.jsonl"
    
    log_info "📝 Aracı yerleşim tablosu (başlangıç) oluşturuluyor..."
    
    mkdir -p ./Agent-shared
    
    # JSONL形式のファイル（コメントなしのピュアなJSONL）
    > "$jsonl_table_file"
    
    # PMエントリ（working_dirは空文字列で初期化）
    echo '{"agent_id": "PM", "tmux_session": "'$PM_SESSION'", "tmux_window": 0, "tmux_pane": 0, "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
    
    # 複数のワーカーセッションのペイン（初期状態）
    local global_agent_count=0
    
    if [ $total_panes -le 12 ]; then
        # 単一セッションの場合
        local pane_indices=($(tmux list-panes -t "${WORKER_SESSION}:hpc-agents" -F "#{pane_index}" 2>/dev/null || echo ""))
        
        for i in "${!pane_indices[@]}"; do
            local pane_id="${pane_indices[$i]}"
            # 全ペインを待機中として登録
            local agent_id="Beklemede$((i + 1))"
            echo '{"agent_id": "'$agent_id'", "tmux_session": "'$WORKER_SESSION'", "tmux_window": 0, "tmux_pane": '$pane_id', "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
        done
    else
        # 複数セッションの場合
        local session_num=1
        local remaining_panes=$total_panes
        
        while [ $remaining_panes -gt 0 ]; do
            local panes_in_session
            if [ $remaining_panes -gt 12 ]; then
                panes_in_session=12
            else
                panes_in_session=$remaining_panes
            fi
            
            local session_name="${WORKER_SESSION_PREFIX}${session_num}"
            
            # セッションが存在する場合のみ処理
            if tmux has-session -t "$session_name" 2>/dev/null; then
                local pane_indices=($(tmux list-panes -t "${session_name}:hpc-agents" -F "#{pane_index}" 2>/dev/null || echo ""))
                
                for i in "${!pane_indices[@]}"; do
                    local pane_id="${pane_indices[$i]}"
                    # 全ペインを待機中として登録
                    global_agent_count=$((global_agent_count + 1))
                    local agent_id="Beklemede${global_agent_count}"
                    echo '{"agent_id": "'$agent_id'", "tmux_session": "'$session_name'", "tmux_window": 0, "tmux_pane": '$pane_id', "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
                done
            fi
            
            remaining_panes=$((remaining_panes - panes_in_session))
            session_num=$((session_num + 1))
        done
    fi
    
    log_success "✅ agent_and_pane_id_table.jsonl oluşturma tamamlandı"
}

# 実行計画表示（シンプル版）
show_execution_plan() {
    local worker_count=$1
    
    echo ""
    echo "📋 セットアップ情報:"
    echo "===================="
    echo "ワーカー数: $worker_count (PM除く)"
    echo "ペイン数: $worker_count"
    echo ""
    echo "参考構成例（実際の配置はPMが決定）:"
    echo "  2人: SE(1) + PG(1) ※最小構成"
    echo "  6人: SE(2) + PG(4)"
    echo "  8人: SE(2) + PG(5) + CD(1)"
    echo "  11人: SE(2) + PG(8) + CD(1)"
    echo "  15人: SE(3) + PG(11) + CD(1)"
    echo ""
    echo "推奨: SEは2人が理想的、PGはプロジェクトの特性に応じて調整"
    echo ""
}

# メイン処理
main() {
    echo "🧬 VibeCodeHPC Multi-Agent HPC Environment Setup"
    echo "==============================================="
    echo ""
    
    # 引数チェック
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    # オプション処理
    local worker_count=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_usage
                exit 0
                ;;
            --project)
                if [[ $# -lt 2 ]]; then
                    log_error "--project オプションにはプロジェクト名が必要です"
                    exit 1
                fi
                PROJECT_NAME="$2"
                USE_DEFAULT_NAMES=false
                shift 2
                ;;
            --hooks)
                if [[ $# -lt 2 ]]; then
                    log_error "--hooks オプションにはバージョン（v2|v3）が必要です"
                    exit 1
                fi
                if [[ "$2" != "v2" && "$2" != "v3" ]]; then
                    log_error "hooksバージョンは v2 または v3 を指定してください"
                    exit 1
                fi
                HOOKS_VERSION="$2"
                shift 2
                ;;
            --periodic-enter)
                if [[ $# -lt 2 ]]; then
                    log_error "--periodic-enter オプションには秒数が必要です"
                    exit 1
                fi
                if ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    log_error "--periodic-enter には数値を指定してください"
                    exit 1
                fi
                PERIODIC_ENTER_INTERVAL="$2"
                shift 2
                ;;
            --clean-only)
                log_info "クリーンアップモード"
                # _old_つきのセッションを削除
                tmux list-sessions 2>/dev/null | grep -E "_old_" | cut -d: -f1 | while read session; do
                    tmux kill-session -t "$session" 2>/dev/null && log_info "${session}削除"
                done
                rm -rf ./tmp/agent*_done.txt 2>/dev/null
                log_success "✅ クリーンアップ完了"
                exit 0
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                if [[ ! "$1" =~ ^[0-9]+$ ]]; then
                    log_error "不明なオプションまたはエージェント数: $1"
                    show_usage
                    exit 1
                fi
                worker_count=$1
                shift
                ;;
        esac
    done
    
    # ワーカー数が指定されていない場合
    if [ -z "$worker_count" ]; then
        log_error "ワーカー数を指定してください"
        show_usage
        exit 1
    fi
    
    # エージェント数チェック（PMを除く、0はシングルエージェントモード）
    if [[ $worker_count -eq 0 ]]; then
        log_info "シングルエージェントモード: PMペインのみ作成"
    elif [[ $worker_count -eq 1 ]]; then
        log_error "エージェント数1は無効です（0:シングルモード、2以上:マルチモード）"
        exit 1
    elif [[ $worker_count -lt 2 ]]; then
        log_error "マルチエージェントモードは2以上を指定してください（PM除く、最小構成: SE + PG）"
        exit 1
    fi
    
    # セッション名を決定
    determine_session_names
    
    # 実行計画表示（シンプル版）
    show_execution_plan $worker_count
    if [ "$USE_DEFAULT_NAMES" = false ]; then
        echo "プロジェクト名: ${PROJECT_NAME}"
        echo "PMセッション名: ${PROJECT_NAME}_PM"
        echo "ワーカーセッション名: ${PROJECT_NAME}_Workers1"
    else
        echo "PMセッション名: $DEFAULT_PM_SESSION (デフォルト)"
        echo "ワーカーセッション名: $DEFAULT_WORKER_SESSION (デフォルト)"
    fi
    echo ""
    
    # dry-runの場合はここで終了
    if [ "$DRY_RUN" = true ]; then
        log_info "dry-runモード: 実際のセットアップは行いません"
        exit 0
    fi
    
    # セッション名の衝突チェック
    if ! check_session_conflicts; then
        log_error "セットアップを中断します"
        exit 1
    fi
    
    # 既存セッションの処理
    handle_existing_sessions
    
    # エージェント数をファイルに記録（PMがリソース配分計画に使用）
    echo "$worker_count" > ./Agent-shared/max_agent_number.txt
    log_info "エージェント数を記録: $worker_count (PM除く)"
    
    # hooksバージョンを記録
    echo "$HOOKS_VERSION" > ./hooks/.hooks_version
    log_info "🎣 hooksバージョンを設定: $HOOKS_VERSION"
    
    # PMセッション作成
    create_pm_session
    
    # シングルモードの場合はワーカーセッション作成をスキップ
    if [[ $worker_count -eq 0 ]]; then
        log_info "シングルエージェントモード: ワーカーセッション作成をスキップ"
        
        # シングルモード用のagent_and_pane_id_table.jsonl生成
        mkdir -p ./Agent-shared
        local jsonl_table_file="./Agent-shared/agent_and_pane_id_table.jsonl"
        > "$jsonl_table_file"
        echo '{"agent_id": "SOLO", "tmux_session": "'$PM_SESSION'", "tmux_window": 0, "tmux_pane": 0, "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
        log_success "✅ シングルモード用agent_and_pane_id_table.jsonl生成完了"
    else
        # ワーカーセッション作成
        local total_panes=$worker_count
        create_worker_sessions $total_panes
        
        # agent_and_pane_id_table.jsonl生成（初期状態）
        generate_agent_pane_table $total_panes
    fi
    
    # 完了メッセージ
    echo ""
    log_success "🎉 VibeCodeHPC環境セットアップ完了！"
    echo ""
    echo "📋 次のステップ:"
    echo "  1. 🔗 セッションアタッチ:"
    if [[ $worker_count -eq 0 ]]; then
        echo "     # シングルエージェントモード"
        echo "     tmux attach-session -t $PM_SESSION"
    else
        echo "     # ターミナルタブ1: PM用"
        echo "     tmux attach-session -t $PM_SESSION"
        echo ""
        echo "     # ターミナルタブ2: その他のエージェント用"
        if [ $total_panes -le 12 ]; then
            echo "     tmux attach-session -t $WORKER_SESSION"
        else
            echo "     tmux attach-session -t ${WORKER_SESSION_PREFIX}1"  # 最初のワーカーセッション
            echo ""
            echo "     # 13体以上の場合、追加セッション:"
            local session_num=2
            local remaining=$((total_panes - 12))
            while [ $remaining -gt 0 ]; do
                echo "     tmux attach-session -t ${WORKER_SESSION_PREFIX}${session_num}"
                remaining=$((remaining - 12))
                session_num=$((session_num + 1))
            done
        fi
    fi
    echo ""
    echo "  2. 🤖 エージェント起動:"
    echo "     # $PM_SESSION で以下を実行:"
    if [[ $worker_count -eq 0 ]]; then
        echo "     ./start_solo.sh"
    else
        echo "     ./start_PM.sh"
    fi
    echo ""
    echo "  3. 📊 エージェント配置:"
    echo "     cat ./Agent-shared/agent_and_pane_id_table.jsonl  # ペイン番号確認（JSONL形式）"
    echo "     cat ./Agent-shared/agent_and_pane_id_table.jsonl # ペイン番号確認"
    echo "     cat ./Agent-shared/max_agent_number.txt          # ワーカー数: $worker_count"
    echo ""
    
    # セッション作成確認
    echo "🔍 セッション作成確認:"
    if tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        echo "  ✅ $PM_SESSION: 作成成功"
    else
        echo "  ❌ $PM_SESSION: 作成失敗"
    fi
    
    # 複数ワーカーセッションの確認
    if [ $total_panes -le 12 ]; then
        if tmux has-session -t "$WORKER_SESSION" 2>/dev/null; then
            echo "  ✅ $WORKER_SESSION: 作成成功"
        else
            echo "  ❌ $WORKER_SESSION: 作成失敗"
        fi
    else
        local session_num=1
        local remaining=$total_panes
        while [ $remaining -gt 0 ]; do
            local session_name="${WORKER_SESSION_PREFIX}${session_num}"
            if tmux has-session -t "$session_name" 2>/dev/null; then
                echo "  ✅ $session_name: 作成成功"
            else
                echo "  ❌ $session_name: 作成失敗"
            fi
            remaining=$((remaining - 12))
            session_num=$((session_num + 1))
        done
    fi
    
    echo ""
    echo "Mevcut tmux oturumları:"
    tmux list-sessions || echo "Oturum yok"
}

main "$@"
