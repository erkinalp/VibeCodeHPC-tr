#!/bin/bash

# 🧬 VibeCodeHPC Multi-Agent HPC Environment Setup
# Dynamic tmux session creation for user-specified agent count

set -e  # Hata durumunda dur

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Küresel değişkenler
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
    
    # PG (Hiyerarşik numaralandırma)
    # SE 1 kişi olduğunda: PG1.1, PG1.2, ...
    # SE 2 kişi olduğunda: SE1 altında → PG1.1, PG1.2, ..., SE2 altında → PG2.1, PG2.2, ...
    local pg_idx=1
    if [ $se_count -eq 1 ]; then
        # Tüm PG'leri SE1 altına yerleştir
        for ((p=1; p<=pg_count; p++)); do
            agents+=("PG1.$((p))")
        done
    else
        # PG'yi her SE'ye eşit olarak dağıtma
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

# Oturum adının belirlenmesi
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

# Oturum adı çakışma kontrolü
check_session_conflicts() {
    local conflicts=false
    
    log_info "🔍 Oturum adlarının çakışması kontrol ediliyor..."
    
    # PM oturumunun kontrolü
    if tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        log_error "❌ '$PM_SESSION' oturumu zaten mevcut"
        conflicts=true
    fi
    
    # Worker oturumunun kontrolü
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

# Oturum tekrar kontrolü ve yeniden adlandırma
handle_existing_sessions() {
    log_info "🔍 Mevcut oturumların kontrolü ve işlenmesi..."
    
    # Dizin hazırlığı
    mkdir -p ./Agent-shared
    mkdir -p ./communication/logs
    mkdir -p ./tmp
    rm -f ./tmp/agent*_done.txt 2>/dev/null
    
    sleep 0.5
    log_success "✅ Oturum hazırlığı tamam"
}

# PM oturumu oluşturma
create_pm_session() {
    log_info "📺 PM oturumu oluşturuluyor: $PM_SESSION"
    
    # Yeni PM oturumu oluşturma
    tmux new-session -d -s "$PM_SESSION" -n "project-manager"
    
    # Oturumun oluşturulup oluşturulmadığını kontrol et
    if ! tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        log_error "${PM_SESSION} oluşturulamadı"
        log_info "Mevcut oturumlar:"
        tmux list-sessions || echo "Oturum yok"
        return 1
    fi
    
    tmux send-keys -t "${PM_SESSION}:project-manager" "cd $PROJECT_ROOT" C-m

    # CLI_HOOKS_MODE ortam değişkenini ayarla (ebeveyn shell'den devralındı veya auto)
    tmux send-keys -t "${PM_SESSION}:project-manager" "export CLI_HOOKS_MODE='${CLI_HOOKS_MODE:-auto}'" C-m

    # bash/zsh uyumlu istem ayarı
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

# Durum gösterimi pane güncelleme fonksiyonu oluşturma
generate_status_display_script() {
    local agents=($1)
    local script_file="./tmp/update_status_display.sh"
    
    cat > "$script_file" << 'EOF'
#!/bin/bash
# Durum gösterimi güncelleme betiği

while true; do
    clear
    echo "[VibeCodeHPC Ajan Yerleşim Şeması]"
    echo "================================"
    
    # TODO: Gerçek yerleşime dayalı olarak dinamik şekilde oluşturulacak
    
    sleep 5
done
EOF
    
    chmod +x "$script_file"
}

# Tek bir işçi oturumu oluşturma (12 pencereye kadar)
create_single_worker_session() {
    local session_name=$1
    local start_pane=$2
    local end_pane=$3
    local panes_in_session=$((end_pane - start_pane + 1))
    
    log_info "📺 Çalışan oturumu oluşturma: $session_name (${panes_in_session}panel)..."
    
    # Sabit düzen hesaplaması
    local cols rows
    if [ $panes_in_session -le 4 ]; then
        cols=2; rows=2
    elif [ $panes_in_session -le 9 ]; then
        cols=3; rows=3
    elif [ $panes_in_session -le 12 ]; then
        cols=4; rows=3  # 4 sütun x 3 satır (varsayılan ayar)
    elif [ $panes_in_session -le 16 ]; then
        cols=4; rows=4
    else
        cols=5; rows=4
    fi
    
    log_info "Izgara yapılandırması: ${cols}sütun x ${rows}satır"
    
    # Oturum oluşturuldu
    tmux new-session -d -s "$session_name" -n "hpc-agents"
    
    # Oturumun oluşturulup oluşturulmadığını kontrol et
    if ! tmux has-session -t "$session_name" 2>/dev/null; then
        log_error "${session_name}oturumu oluşturulamadı"
        return 1
    fi
    
    sleep 1
    
    # Izgara oluşturma (hata yönetimi ile birlikte)
    local pane_count=1
    local creation_failed=false
    
    # İlk sütunu oluşturuyor
    for ((j=1; j < rows && pane_count < panes_in_session; j++)); do
        if ! tmux split-window -v -t "${session_name}:hpc-agents" 2>&1 | grep -q "no space for new pane"; then
            ((pane_count++))
        else
            log_error "⚠️ Panel oluşturma başarısız: no space for new pane (panel $pane_count/$panes_in_session)"
            creation_failed=true
            break
        fi
    done
    
    # Kalan sütunları oluştur (sadece ilk sütunda hata yoksa)
    if [ "$creation_failed" = false ]; then
        for ((i=1; i < cols && pane_count < panes_in_session; i++)); do
            tmux select-pane -t "${session_name}:hpc-agents.0"
            if ! tmux split-window -h -t "${session_name}:hpc-agents" 2>&1 | grep -q "no space for new pane"; then
                ((pane_count++))
            else
                log_error "⚠️ Panel oluşturma başarısız: no space for new pane (panel $pane_count/$panes_in_session)"
                creation_failed=true
                break
            fi
            
            if [ "$creation_failed" = false ]; then
                for ((j=1; j < rows && pane_count < panes_in_session; j++)); do
                    if ! tmux split-window -v -t "${session_name}:hpc-agents" 2>&1 | grep -q "no space for new pane"; then
                        ((pane_count++))
                    else
                        log_error "⚠️ Panel oluşturma başarısız: no space for new pane (panel $pane_count/$panes_in_session)"
                        creation_failed=true
                        break
                    fi
                done
            fi
        done
    fi
    
    # Pane oluşturma başarısız olursa, oluşturulabilen pane sayısını döndürür
    if [ "$creation_failed" = true ]; then
        log_error "❌ İstenen ${panes_in_session} panel arasından sadece ${pane_count} panel oluşturulabilir"
        # Oturumu sil ve hata döndür
        tmux kill-session -t "$session_name" 2>/dev/null
        return 1
    fi
    
    # Düzen ayarı
    tmux select-layout -t "${session_name}:hpc-agents" tiled
    
    # Tüm panellerin başlatılması
    local pane_indices=($(tmux list-panes -t "${session_name}:hpc-agents" -F "#{pane_index}"))
    
    for i in "${!pane_indices[@]}"; do
        local pane_index="${pane_indices[$i]}"
        local pane_target="${session_name}:hpc-agents.${pane_index}"
        
        tmux send-keys -t "$pane_target" "cd $PROJECT_ROOT" C-m

        # OpenTelemetry ortam değişkenlerini ayarla (tüm paneller için ortak)
        tmux send-keys -t "$pane_target" "export CLAUDE_CODE_ENABLE_TELEMETRY=1" C-m
        tmux send-keys -t "$pane_target" "export OTEL_METRICS_EXPORTER=otlp" C-m
        tmux send-keys -t "$pane_target" "export OTEL_METRIC_EXPORT_INTERVAL=10000" C-m
        tmux send-keys -t "$pane_target" "export OTEL_LOGS_EXPORTER=otlp" C-m
        tmux send-keys -t "$pane_target" "export OTEL_LOG_USER_PROMPTS=0" C-m
        tmux send-keys -t "$pane_target" "export OTEL_EXPORTER_OTLP_PROTOCOL=grpc" C-m
        tmux send-keys -t "$pane_target" "export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317" C-m

        # CLI_HOOKS_MODE ortam değişkenini ayarla (ebeveyn shell'den devralındı veya auto)
        tmux send-keys -t "$pane_target" "export CLI_HOOKS_MODE='${CLI_HOOKS_MODE:-auto}'" C-m

        # Tüm panelleri işçi için ayarla
        local global_pane_num=$((start_pane + i))
        if false; then  # Eski kod (bakım için)
            # Eski kod
            tmux select-pane -t "$pane_target" -T "STATUS"
            # bash/zsh uyumlu istem ayarı
            tmux send-keys -t "$pane_target" "if [ -n \"\$ZSH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PROMPT=$'%{\033[1;37m%}(STATUS)%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '" C-m
            tmux send-keys -t "$pane_target" "elif [ -n \"\$BASH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PS1='(\[\033[1;37m\]STATUS\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
            tmux send-keys -t "$pane_target" "fi" C-m
            tmux send-keys -t "$pane_target" "clear" C-m
            tmux send-keys -t "$pane_target" "echo '[VibeCodeHPC Aracı Yerleşim Durumu]'" C-m
            tmux send-keys -t "$pane_target" "echo '================================'" C-m
            tmux send-keys -t "$pane_target" "echo 'PM aracıları yerleştiriyor...'" C-m
            tmux send-keys -t "$pane_target" "echo ''" C-m
            # Global değişkenlere referans (create_worker_sessions içinde ayarlandı)
            tmux send-keys -t "$pane_target" "echo 'Çalışan sayısı: $GLOBAL_TOTAL_WORKERS'" C-m
            tmux send-keys -t "$pane_target" "echo 'directory_pane_map.md dosyasına bakın'" C-m
        else
            # Diğer paneller ajan yerleşimi bekliyor
            local pane_number=$global_pane_num
            tmux select-pane -t "$pane_target" -T "Pane${pane_number}"
            
            # Ajan için OTEL_RESOURCE_ATTRIBUTES hazırlığı (daha sonra agent_id belirlendiğinde güncellenecek)
            tmux send-keys -t "$pane_target" "export TMUX_PANE_ID='${pane_index}'" C-m
            tmux send-keys -t "$pane_target" "export OTEL_RESOURCE_ATTRIBUTES=\"tmux_pane=\${TMUX_PANE},pane_index=${pane_index}\"" C-m
            
            # bash/zsh uyumlu istem ayarı
            tmux send-keys -t "$pane_target" "if [ -n \"\$ZSH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PROMPT=$'%{\033[1;90m%}(Beklemede${pane_number})%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '" C-m
            tmux send-keys -t "$pane_target" "elif [ -n \"\$BASH_VERSION\" ]; then" C-m
            tmux send-keys -t "$pane_target" "  export PS1='(\[\033[1;90m\]Beklemede${pane_number}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
            tmux send-keys -t "$pane_target" "fi" C-m
            tmux send-keys -t "$pane_target" "clear" C-m
            tmux send-keys -t "$pane_target" "echo '=== Aracı yerleşimi bekleniyor (Pane ${pane_number}) ==='" C-m
            tmux send-keys -t "$pane_target" "echo ''" C-m
            tmux send-keys -t "$pane_target" "echo 'PM, yerleşimi directory_pane_map.md üzerinden belirleyecek'" C-m
            tmux send-keys -t "$pane_target" "echo 'Ardından aracı başlatılacaktır'" C-m
            tmux send-keys -t "$pane_target" "echo ''" C-m
            tmux send-keys -t "$pane_target" "echo '📊 OpenTelemetry etkin'" C-m
            tmux send-keys -t "$pane_target" "echo '   OTLP uç noktası: http://localhost:4317'" C-m
        fi
    done
    
    log_success "✅ Çalışan oturumu oluşturma tamamlandı: $session_name"
    return 0
}

# Birden fazla işçi oturumu oluşturma (ana fonksiyon)
create_worker_sessions() {
    local total_panes=$1  # Kullanıcı girişi sayısı + 1 (STATUS için)
    
    # Toplam işçi sayısını global değişken olarak kaydet
    GLOBAL_TOTAL_WORKERS=$((total_panes - 1))
    
    # Öncelikle tek bir oturumda deneme yapın
    log_info "🔧 Tek oturumda oluşturma denemesi yapılıyor..."
    if create_single_worker_session "$WORKER_SESSION" 0 $((total_panes - 1)); then
        log_success "✅ Tek oturumda oluşturma başarılı"
        return 0
    fi
    
    # Tek bir oturumda başarısız olunursa, otomatik olarak birden fazla oturuma bölünür
    log_info "📦 'no space for new pane' hatası tespit edildi. Otomatik olarak birden çok oturuma bölünüyor"
    
    # Daha küçük pane sayısıyla yeniden dene
    local max_panes_per_session=12
    local test_panes=12
    
    # Gerçekten oluşturulabilir maksimum pencere sayısını araştır (12'den başlayarak sırayla azaltıp dene)
    while [ $test_panes -ge 4 ]; do
        log_info "🔍 ${test_panes} panel ile test..."
        local test_session="${WORKER_SESSION_PREFIX}_test"
        
        # Test oturumu oluşturma
        tmux new-session -d -s "$test_session" -n "test" 2>/dev/null
        
        local test_success=true
        local pane_count=1
        
        # Düzen testi (4x3 temel alınarak)
        local cols=4
        local rows=3
        if [ $test_panes -le 9 ]; then
            cols=3; rows=3
        elif [ $test_panes -le 6 ]; then
            cols=3; rows=2
        elif [ $test_panes -le 4 ]; then
            cols=2; rows=2
        fi
        
        # Pane oluşturma testi
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
        
        # Test oturumu silme
        tmux kill-session -t "$test_session" 2>/dev/null
        
        if [ "$test_success" = true ]; then
            max_panes_per_session=$test_panes
            log_success "✅ Oturum başına en fazla ${max_panes_per_session} panel oluşturulabilir"
            break
        fi
        
        # Bir sonraki denemede 3 panel azaltılacak
        test_panes=$((test_panes - 3))
    done
    
    # Birden fazla oturuma bölerek oluşturma
    log_info "📦 ${max_panes_per_session} panel başına bölünerek oluşturulacak"
    
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

# agent_and_pane_id_table oluşturma (ilk durum, çoklu oturum desteği)
generate_agent_pane_table() {
    local total_panes=$1
    
    local jsonl_table_file="./Agent-shared/agent_and_pane_id_table.jsonl"
    
    log_info "📝 Aracı yerleşim tablosu (başlangıç) oluşturuluyor..."
    
    mkdir -p ./Agent-shared
    
    # JSONL formatında dosya (yorum içermeyen saf JSONL)
    > "$jsonl_table_file"
    
    # PM girişi (working_dir boş bir dize ile başlatılır)
    echo '{"agent_id": "PM", "tmux_session": "'$PM_SESSION'", "tmux_window": 0, "tmux_pane": 0, "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
    
    # Birden fazla işçi oturumunun panelleri (başlangıç durumu)
    local global_agent_count=0
    
    if [ $total_panes -le 12 ]; then
        # Tek oturum durumunda
        local pane_indices=($(tmux list-panes -t "${WORKER_SESSION}:hpc-agents" -F "#{pane_index}" 2>/dev/null || echo ""))
        
        for i in "${!pane_indices[@]}"; do
            local pane_id="${pane_indices[$i]}"
            # Tüm panelleri beklemede olarak kaydet
            local agent_id="Beklemede$((i + 1))"
            echo '{"agent_id": "'$agent_id'", "tmux_session": "'$WORKER_SESSION'", "tmux_window": 0, "tmux_pane": '$pane_id', "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
        done
    else
        # Birden fazla oturum durumunda
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
            
            # Oturum mevcutsa işlem yapılır
            if tmux has-session -t "$session_name" 2>/dev/null; then
                local pane_indices=($(tmux list-panes -t "${session_name}:hpc-agents" -F "#{pane_index}" 2>/dev/null || echo ""))
                
                for i in "${!pane_indices[@]}"; do
                    local pane_id="${pane_indices[$i]}"
                    # Tüm panelleri beklemede olarak kaydet
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

# Çalıştırma planı görüntüleme (Basit sürüm)
show_execution_plan() {
    local worker_count=$1
    
    echo ""
    echo "📋 Kurulum bilgileri:"
    echo "===================="
    echo "İşçi sayısı: $worker_count (PM hariç)"
    echo "Panel sayısı: $worker_count"
    echo ""
    echo "Örnek yapılandırmalar (nihai yerleşimi PM belirler):"
    echo "  2 kişi: SE(1) + PG(1) [en küçük yapı]"
    echo "  6 kişi: SE(2) + PG(4)"
    echo "  8 kişi: SE(2) + PG(5) + CD(1)"
    echo "  11 kişi: SE(2) + PG(8) + CD(1)"
    echo "  15 kişi: SE(3) + PG(11) + CD(1)"
    echo ""
    echo "Öneri: SE için 2 kişi idealdir, PG sayısını projenin özelliklerine göre ayarlayın"
    echo ""
}

# Ana işlem
main() {
    echo "🧬 VibeCodeHPC Multi-Agent HPC Environment Setup"
    echo "==============================================="
    echo ""
    
    # Argüman kontrolü
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    # Seçenek işlemi
    local worker_count=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_usage
                exit 0
                ;;
            --project)
                if [[ $# -lt 2 ]]; then
                    log_error "--project seçeneği için proje adı gerekli"
                    exit 1
                fi
                PROJECT_NAME="$2"
                USE_DEFAULT_NAMES=false
                shift 2
                ;;
            --hooks)
                if [[ $# -lt 2 ]]; then
                    log_error "--hooks seçeneği için sürüm (v2|v3) gerekli"
                    exit 1
                fi
                if [[ "$2" != "v2" && "$2" != "v3" ]]; then
                    log_error "hooks sürümü v2 veya v3 olmalıdır"
                    exit 1
                fi
                HOOKS_VERSION="$2"
                shift 2
                ;;
            --periodic-enter)
                if [[ $# -lt 2 ]]; then
                    log_error "--periodic-enter seçeneği için saniye değeri gerekli"
                    exit 1
                fi
                if ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    log_error "--periodic-enter için sayısal bir değer belirtin"
                    exit 1
                fi
                PERIODIC_ENTER_INTERVAL="$2"
                shift 2
                ;;
            --clean-only)
                log_info "Temizlik modu"
                tmux list-sessions 2>/dev/null | grep -E "_old_" | cut -d: -f1 | while read session; do
                    tmux kill-session -t "$session" 2>/dev/null && log_info "${session} silindi"
                done
                rm -rf ./tmp/agent*_done.txt 2>/dev/null
                log_success "✅ Temizlik tamamlandı"
                exit 0
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                if [[ ! "$1" =~ ^[0-9]+$ ]]; then
                    log_error "Bilinmeyen seçenek veya ajan sayısı: $1"
                    show_usage
                    exit 1
                fi
                worker_count=$1
                shift
                ;;
        esac
    done
    
    # Eğer işçi sayısı belirtilmemişse
    if [ -z "$worker_count" ]; then
        log_error "İşçi sayısını belirtin"
        show_usage
        exit 1
    fi
    
    # Ajan sayısı kontrolü (PM hariç, 0 tek ajan modu)
    if [[ $worker_count -eq 0 ]]; then
        log_info "Tek ajan modu: yalnızca PM paneli oluşturulacak"
    elif [[ $worker_count -eq 1 ]]; then
        log_error "Ajan sayısı 1 geçersizdir (0: tek mod, 2 ve üzeri: çok aracılı mod)"
        exit 1
    elif [[ $worker_count -lt 2 ]]; then
        log_error "Çok aracılı mod için en az 2 belirtin (PM hariç, minimum: SE + PG)"
        exit 1
    fi
    
    # Oturum adını belirle
    determine_session_names
    
    # Çalıştırma planı görüntüleme (Basit sürüm)
    show_execution_plan $worker_count
    if [ "$USE_DEFAULT_NAMES" = false ]; then
        echo "Proje adı: ${PROJECT_NAME}"
        echo "PM oturum adı: ${PROJECT_NAME}_PM"
        echo "İşçi oturum adı: ${PROJECT_NAME}_Workers1"
    else
        echo "PM oturum adı: $DEFAULT_PM_SESSION (varsayılan)"
        echo "İşçi oturum adı: $DEFAULT_WORKER_SESSION (varsayılan)"
    fi
    echo ""
    
    # dry-run durumunda burada sonlandırılır
    if [ "$DRY_RUN" = true ]; then
        log_info "dry-run modu: gerçek kurulum yapılmayacak"
        exit 0
    fi
    
    # Oturum adı çakışma kontrolü
    if ! check_session_conflicts; then
        log_error "Kurulum durduruluyor"
        exit 1
    fi
    
    # Mevcut oturumun işlenmesi
    handle_existing_sessions
    
    # Ajan sayısını dosyaya kaydet (PM kaynak tahsis planlamasında kullanır)
    echo "$worker_count" > ./Agent-shared/max_agent_number.txt
    log_info "Ajan sayısı kaydedildi: $worker_count (PM hariç)"
    
    # hooks sürümünü kaydet
    echo "$HOOKS_VERSION" > ./hooks/.hooks_version
    log_info "🎣 hooks sürümü ayarlandı: $HOOKS_VERSION"
    
    # PM oturumu oluşturma
    create_pm_session
    
    # Tek mod durumunda worker oturumu oluşturmayı atla
    if [[ $worker_count -eq 0 ]]; then
        log_info "Tek ajan modu: işçi oturumu oluşturma atlandı"
        
        # Tek mod için agent_and_pane_id_table.jsonl oluşturma
        mkdir -p ./Agent-shared
        local jsonl_table_file="./Agent-shared/agent_and_pane_id_table.jsonl"
        > "$jsonl_table_file"
        echo '{"agent_id": "SOLO", "tmux_session": "'$PM_SESSION'", "tmux_window": 0, "tmux_pane": 0, "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
        log_success "✅ Tek mod için agent_and_pane_id_table.jsonl oluşturma tamamlandı"
    else
        # Çalışan oturumu oluşturma
        local total_panes=$worker_count
        create_worker_sessions $total_panes
        
        # agent_and_pane_id_table.jsonl oluşturma (ilk durum)
        generate_agent_pane_table $total_panes
    fi
    
    # Tamamlama mesajı
    echo ""
    log_success "🎉 VibeCodeHPC ortam kurulumu tamamlandı!"
    echo ""
    echo "📋 Sonraki adımlar:"
    echo "  1. 🔗 Oturuma bağlan:"
    if [[ $worker_count -eq 0 ]]; then
        echo "     # Tek ajan modu"
        echo "     tmux attach-session -t $PM_SESSION"
    else
        echo "     # Terminal sekmesi 1: PM için"
        echo "     tmux attach-session -t $PM_SESSION"
        echo ""
        echo "     # Terminal sekmesi 2: diğer ajanlar için"
        if [ $total_panes -le 12 ]; then
            echo "     tmux attach-session -t $WORKER_SESSION"
        else
            echo "     tmux attach-session -t ${WORKER_SESSION_PREFIX}1"  # İlk işçi oturumu
            echo ""
            echo "     # 13+ durumda ek oturumlar:"
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
    echo "  2. 🤖 Ajan başlatma:"
    echo "     # $PM_SESSION içinde şunları çalıştırın:"
    if [[ $worker_count -eq 0 ]]; then
        echo "     ./start_solo.sh"
    else
        echo "     ./start_PM.sh"
    fi
    echo ""
    echo "  3. 📊 Ajan yerleşimi:"
    echo "     cat ./Agent-shared/agent_and_pane_id_table.jsonl  # Panel numarası kontrolü (JSONL)"
    echo "     cat ./Agent-shared/agent_and_pane_id_table.jsonl # Panel numarası kontrolü"
    echo "     cat ./Agent-shared/max_agent_number.txt          # İşçi sayısı: $worker_count"
    echo ""
    
    # Oturum oluşturma doğrulaması
    echo "🔍 Oturum oluşturma doğrulaması:"
    if tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        echo "  ✅ $PM_SESSION: Oluşturma başarılı"
    else
        echo "  ❌ $PM_SESSION: Oluşturma başarısız"
    fi
    
    # Birden fazla işçi oturumunun kontrolü
    if [ $total_panes -le 12 ]; then
        if tmux has-session -t "$WORKER_SESSION" 2>/dev/null; then
            echo "  ✅ $WORKER_SESSION: Oluşturma başarılı"
        else
            echo "  ❌ $WORKER_SESSION: Oluşturma başarısız"
        fi
    else
        local session_num=1
        local remaining=$total_panes
        while [ $remaining -gt 0 ]; do
            local session_name="${WORKER_SESSION_PREFIX}${session_num}"
            if tmux has-session -t "$session_name" 2>/dev/null; then
                echo "  ✅ $session_name: Oluşturma başarılı"
            else
                echo "  ❌ $session_name: Oluşturma başarısız"
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
