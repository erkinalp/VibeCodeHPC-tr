#!/bin/bash

# 🧬 VibeCodeHPC Aracılar arası mesaj gönderim sistemi

# agent_and_pane_id_table.jsonl yükleme
load_agent_map() {
    local table_file="./Agent-shared/agent_and_pane_id_table.jsonl"
    
    if [[ ! -f "$table_file" ]]; then
        echo "❌ Hata: agent_and_pane_id_table.jsonl bulunamadı" >&2
        echo "Lütfen önce ./communication/setup.sh komutunu çalıştırın" >&2
        return 1
    fi
    
    if [[ ! -r "$table_file" ]]; then
        echo "❌ Hata: agent_and_pane_id_table.jsonl okunamıyor" >&2
        return 1
    fi
    
    declare -gA AGENT_MAP
    local line_number=0
    local valid_entries=0
    
    while IFS= read -r line; do
        ((line_number++))
        
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        if [[ ! "$line" =~ ^\{.*\}$ ]]; then
            echo "⚠️  Uyarı: Satır $line_number geçersiz JSON formatı" >&2
            continue
        fi
        
        local agent_name=""
        local session=""
        local window=""
        local pane=""
        
        if [[ "$line" =~ \"agent_id\":[[:space:]]*\"([^\"]+)\" ]]; then
            agent_name="${BASH_REMATCH[1]}"
        else
            echo "⚠️  Uyarı: Satır $line_number agent_id içermiyor" >&2
            continue
        fi
        
        if [[ "$line" =~ \"tmux_session\":[[:space:]]*\"([^\"]+)\" ]]; then
            session="${BASH_REMATCH[1]}"
        fi
        
        if [[ "$line" =~ \"tmux_window\":[[:space:]]*([0-9]+) ]]; then
            window="${BASH_REMATCH[1]}"
        fi
        
        if [[ "$line" =~ \"tmux_pane\":[[:space:]]*([0-9]+) ]]; then
            pane="${BASH_REMATCH[1]}"
        fi
        
        if [[ -n "$agent_name" && -n "$session" && -n "$window" && -n "$pane" ]]; then
            AGENT_MAP["$agent_name"]="$session:$window.$pane"
            ((valid_entries++))
        else
            echo "⚠️  Uyarı: Satır $line_number eksik alan içeriyor (agent: $agent_name)" >&2
        fi
    done < "$table_file"
    
    if [[ $valid_entries -eq 0 ]]; then
        echo "❌ Hata: Geçerli aracı girişi bulunamadı" >&2
        return 1
    fi
    
    echo "✅ $valid_entries aracı yüklendi" >&2
    return 0
}

get_agent_target() {
    local agent_name="$1"
    
    agent_name=$(echo "$agent_name" | tr '[:lower:]' '[:upper:]')
    
    # AGENT_MAP içinden al
    if [[ -n "${AGENT_MAP[$agent_name]}" ]]; then
        echo "${AGENT_MAP[$agent_name]}"
    else
        echo ""
    fi
}

get_agent_role() {
    local agent_name="$1"
    
    case "${agent_name:0:2}" in
        "PM") echo "Proje yönetimi ve gereksinim tanımı" ;;
        "SE") echo "Sistem tasarımı ve izleme" ;;
        "PG") echo "Kod üretimi ve optimizasyon" ;;
        "CD") echo "GitHub ve dağıtım yönetimi" ;;
        *) echo "Uzman aracı" ;;
    esac
}

get_agent_color() {
    local agent_name="$1"
    
    case "${agent_name:0:2}" in
        "PM") echo "1;35" ;;  # Macenta
        "SE") echo "1;36" ;;  # Camgöbeği
        "PG") 
            if [[ "$agent_name" =~ PG1\.1 ]]; then
                echo "1;32"  # Yeşil
            elif [[ "$agent_name" =~ PG1\.2 ]]; then
                echo "1;92"  # Açık yeşil
            elif [[ "$agent_name" =~ PG2\. ]]; then
                echo "1;33"  # Sarı
            else
                echo "1;32"  # Varsayılan yeşil
            fi
            ;;
        "CD") echo "1;31" ;;  # Kırmızı
        *) echo "1;37" ;;     # Beyaz
    esac
}

show_usage() {
    cat << EOF
🧬 VibeCodeHPC Aracılar arası mesaj gönderim sistemi

Kullanım:
  $0 [aracı_adı] [mesaj]
  $0 --list
  $0 --status
  $0 --broadcast [mesaj]

Temel komutlar:
  PM "requirement_definition.md dosyasını lütfen kontrol edin"
  SE1 "İzleme durumunu lütfen rapor edin"
  PG1.1.1 "Lütfen kod optimizasyonuna başlayın"
  CD "Lütfen GitHub senkronizasyonunu çalıştırın"

Özel komutlar:
  --list        : Kullanılabilir aracılar listesini gösterir
  --status      : Tüm aracıların durumunu gösterir
  --broadcast   : Tüm aracılara mesaj gönderir
  --help        : Bu yardım ekranını gösterir

Mesaj türleri (önerilen format):
  [İstek] Derlemeyi çalıştırın lütfen
  [Rapor] SOTA güncellemesi: 285.7 GFLOPS elde edildi
  [Soru] visible_paths.txt nasıl güncellenir?
  [Tamamlandı] Proje başlatma tamamlandı

Özel komutlar (PM yönetimi için):
  "!cd /path/to/directory"              # Aracıyı yeniden konumlandırma (durum korunur)
  
Not: Yeniden konumlandırma, her aracının mevcut konumundan yapılır

Örnekler:
  $0 SE1 "[İstek] PG1.1.1’e OpenMP optimizasyon görevini dağıtın lütfen"
  $0 PG1.1.1 "[Soru] OpenACC paralelleştirme uyarısı var. Nasıl ilerleyelim?"
  $0 PG1.1 "[Rapor] job_12345 tamamlandı, performans verisi: 285.7 GFLOPS"
  
  $0 PG1.1.1 "!cd /absolute/path/to/VibeCodeHPC/Flow/TypeII/single-node/gcc/OpenMP_MPI"
  
  $0 PG1.2.1 "!cd ../../../gcc/CUDA"          # Aynı hiyerarşide başka stratejiye geç
  $0 SE1 "!cd ../multi-node"                  # Üst hiyerarşiye geç
  
  $0 --broadcast "[Acil] Tüm aracıların durum raporunu iletin"
EOF
}

show_agents() {
    echo "📋 VibeCodeHPC Aracı Listesi:"
    echo "================================"
    
    if [[ ${#AGENT_MAP[@]} -eq 0 ]]; then
        echo "❌ Aracı bulunamadı"
        echo "Lütfen önce ./communication/setup.sh komutunu çalıştırın"
        return 1
    fi
    
    local agent_types=("PM" "SE" "PG" "CD")
    
    for type in "${agent_types[@]}"; do
        echo ""
        echo "📍 ${type} Aracılar:"
        local found=false
        
        for agent in "${!AGENT_MAP[@]}"; do
            if [[ "$agent" =~ ^${type} ]]; then
                local target="${AGENT_MAP[$agent]}"
                local role=$(get_agent_role "$agent")
                local color=$(get_agent_color "$agent")
                
                local session="${target%%:*}"
                if tmux has-session -t "$session" 2>/dev/null; then
                    echo -e "  \033[${color}m$agent\033[0m → $target ($role)"
                else
                    echo -e "  \033[${color}m$agent\033[0m → [başlatılmadı] ($role)"
                fi
                found=true
            fi
        done
        
        if [[ "$found" == false ]]; then
            echo "  (Uygun aracı yok)"
        fi
    done
    
    echo ""
    echo "Toplam aracı sayısı: ${#AGENT_MAP[@]}"
}

show_status() {
    echo "📊 VibeCodeHPC Aracı Durumu:"
    echo "================================"
    
    if [[ ${#AGENT_MAP[@]} -eq 0 ]]; then
        echo "❌ Aracı bulunamadı"
        return 1
    fi
    
    local active_count=0
    local total_count=${#AGENT_MAP[@]}
    
    for agent in "${!AGENT_MAP[@]}"; do
        local target="${AGENT_MAP[$agent]}"
        local session="${target%%:*}"
        local window_pane="${target##*:}"
        local window="${window_pane%%.*}"
        local pane="${window_pane##*.}"
        
        if tmux has-session -t "$session" 2>/dev/null; then
            if tmux list-panes -t "$session:$window" -F "#{pane_index}" 2>/dev/null | grep -q "^$pane$"; then
                echo "✅ $agent : aktif"
                ((active_count++))
            else
                echo "⚠️  $agent : oturum var, pencere/pane bilinmiyor"
            fi
        else
            echo "❌ $agent : başlatılmamış"
        fi
    done
    
    echo ""
    echo "Aktif: $active_count / $total_count"
    
    echo ""
    echo "📺 tmux oturum bilgileri:"
    tmux list-sessions 2>/dev/null | while IFS=: read -r session rest; do
        local pane_count=$(tmux list-panes -t "$session" 2>/dev/null | wc -l)
        echo "$session: $pane_count panes"
    done
}

broadcast_message() {
    local message="$1"
    local sent_count=0
    local failed_count=0
    
    echo "📢 Yayın gönderimi başlatıldı: '$message'"
    echo "================================"
    
    for agent in "${!AGENT_MAP[@]}"; do
        local target="${AGENT_MAP[$agent]}"
        
        if send_message "$target" "$message" "$agent"; then
            ((sent_count++))
        else
            ((failed_count++))
        fi
    done
    
    echo ""
    echo "📊 Yayın sonuçları:"
    echo "  Başarılı: $sent_count"
    echo "  Başarısız: $failed_count"
    echo "  Toplam: $((sent_count + failed_count))"
}

send_message() {
    local target="$1"
    local message="$2"
    local agent_name="$3"
    
    local session="${target%%:*}"
    local window_pane="${target##*:}"
    local window="${window_pane%%.*}"
    local pane="${window_pane##*.}"
    
    if ! tmux has-session -t "$session" 2>/dev/null; then
        echo "❌ $agent_name: Oturum '$session' bulunamadı"
        return 1
    fi
    
    if ! tmux list-panes -t "$session:$window" -F "#{pane_index}" 2>/dev/null | grep -q "^$pane$"; then
        echo "❌ $agent_name: Pencere/pane '$pane' bulunamadı"
        return 1
    fi
    
    echo "📤 $agent_name ← '$message'"
    
    # Mesaj gönderimi     # Mesaj gönderimi (temizleme gerekmez - yeni giriş otomatik olarak değiştirilir)
    tmux send-keys -t "$session:$window.$pane" "$message"
    sleep 0.1
    
    tmux send-keys -t "$session:$window.$pane" C-m
    sleep 0.3
    
    return 0
}

log_message() {
    local agent="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    mkdir -p ./communication/logs
    echo "[$timestamp] $agent: \"$message\"" >> ./communication/logs/send_log.txt
}

main() {
    # agent_and_pane_id_table.jsonl yükleme
    if ! load_agent_map; then
        exit 1
    fi
    
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    case "$1" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --list|-l)
            show_agents
            exit 0
            ;;
        --status|-s)
            show_status
            exit 0
            ;;
        --broadcast|-b)
            if [[ $# -lt 2 ]]; then
                echo "❌ Yayın için bir mesaj gereklidir"
                exit 1
            fi
            broadcast_message "$2"
            exit 0
            ;;
        *)
            if [[ $# -lt 2 ]]; then
                echo "❌ Aracı adı ve mesaj gereklidir"
                show_usage
                exit 1
            fi
            ;;
    esac
    
    local agent_name="$1"
    local message="$2"
    
    agent_name=$(echo "$agent_name" | tr '[:lower:]' '[:upper:]')
    
    local target=$(get_agent_target "$agent_name")
    
    if [[ -z "$target" ]]; then
        echo "❌ Hata: Bilinmeyen aracı '$agent_name'"
        echo "Kullanılabilir aracılar: $0 --list"
        exit 1
    fi
    
    if send_message "$target" "$message" "$agent_name"; then
        log_message "$agent_name" "$message"
        echo "✅ Gönderim tamamlandı: $agent_name"
    else
        echo "❌ Gönderim başarısız: $agent_name"
        exit 1
    fi
}

main "$@"
