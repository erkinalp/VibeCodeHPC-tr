#!/bin/bash

# 🧬 VibeCodeHPC Aracılar arası mesaj gönderim sistemi

# agent_and_pane_id_table.jsonl yükleme
load_agent_map() {
    local table_file="./Agent-shared/agent_and_pane_id_table.jsonl"
    
    if [[ ! -f "$table_file" ]]; then
        echo "❌ Hata: agent_and_pane_id_table.jsonl bulunamadı"
        echo "Lütfen önce ./communication/setup.sh komutunu çalıştırın"
        return 1
    fi
    
    declare -gA AGENT_MAP
    
    while IFS= read -r line; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        if [[ "$line" =~ \"agent_id\":[[:space:]]*\"([^\"]+)\" ]]; then
            local agent_name="${BASH_REMATCH[1]}"
            
            if [[ "$line" =~ \"tmux_session\":[[:space:]]*\"([^\"]+)\" ]]; then
                local session="${BASH_REMATCH[1]}"
            fi
            
            if [[ "$line" =~ \"tmux_window\":[[:space:]]*([0-9]+) ]]; then
                local window="${BASH_REMATCH[1]}"
            fi
            
            if [[ "$line" =~ \"tmux_pane\":[[:space:]]*([0-9]+) ]]; then
                local pane="${BASH_REMATCH[1]}"
            fi
            
            if [[ -n "$agent_name" && -n "$session" && -n "$window" && -n "$pane" ]]; then
                AGENT_MAP["$agent_name"]="$session:$window.$pane"
            fi
        fi
    done < "$table_file"
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
                echo "1;32"  # デフォルト緑
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
  [İstek]  [依頼] コンパイルDerlemeyi çalıştırın lütfen
  [Rapor]  [報告] SOTA更新: 285.7 GFLOPS達成elde edildi
  [Soru]  [質問] visible_paths.txtの更新方 nasıl güncellenir?
  [Tamamlandı]  [完了] プロジェクProje başlatma tamamlandı

Özel komutlar (PM yönetimi için):
  "!cd /path/to/directory"              # Aracıyı yeniden konumlandırma (durum korunur)
  
Not: Yeniden konumlandırma, her aracının mevcut konumundan yapılır

Örnekler:
  $0 SE1 "[İstek]  $0 SE1 "[依頼] PG1.1.1にOpenMP最OpenMP optimizasyon görevini dağıtın lütfen"
  $0 PG1.1.1 "[Soru]  $0 PG1.1.1 "[質問] OpenACCの並列化警告がparalelleştirme uyarısı var. Nasıl ilerleyelim?"
  $0 PG1.1 "[Rapor]  $0 PG1.1 "[報告] job_12345 実行完了çalışma tamamlandı, performans verisi能データ 285.7 GFLOPS達成"
  
  # 再配置例（絶対パス）
  $0 PG1.1.1 "!cd /absolute/path/to/VibeCodeHPC/Flow/TypeII/single-node/gcc/OpenMP_MPI"
  
  # 再配置例（相対パス - エージェントの現在位置から）
  $0 PG1.2.1 "!cd ../../../gcc/CUDA"          # 同階層の別戦略へ移動
  $0 SE1 "!cd ../multi-node"                  # 上位階層へ移動
  
  $0 --broadcast "[緊急] 全エージェント状況報告してください"Rapor 全エージェント状況報告してください"
EOF
}

# エージェント一覧表示
show_agents() {
    echo "📋 VibeCodeHPC エージェント一覧:"
    echo "================================"
    
    if [[ ${#AGENT_MAP[@]} -eq 0 ]]; then
        echo "❌ エージェントが見つかりません"
        echo "Lütfen önce ./communication/setup.sh komutunu çalıştırın"
        return 1
    fi
    
    # エージェント種別ごとに表示
    local agent_types=("PM" "SE" "PG" "CD")
    
    for type in "${agent_types[@]}"; do
        echo ""
        echo "📍 ${type} エージェント:"
        local found=false
        
        for agent in "${!AGENT_MAP[@]}"; do
            if [[ "$agent" =~ ^${type} ]]; then
                local target="${AGENT_MAP[$agent]}"
                local role=$(get_agent_role "$agent")
                local color=$(get_agent_color "$agent")
                
                # セッション存在確認
                local session="${target%%:*}"
                if tmux has-session -t "$session" 2>/dev/null; then
                    echo -e "  \033[${color}m$agent\033[0m → $target ($role)"
                else
                    echo -e "  \033[${color}m$agent\033[0m → [未起動] ($role)"
                fi
                found=true
            fi
        done
        
        if [[ "$found" == false ]]; then
            echo "  (該当エージェントなし)"
        fi
    done
    
    echo ""
    echo "総エージェント数: ${#AGENT_MAP[@]}"
}

# エージェント状態確認
show_status() {
    echo "📊 VibeCodeHPC エージェント状態:"
    echo "================================"
    
    if [[ ${#AGENT_MAP[@]} -eq 0 ]]; then
        echo "❌ エージェントが見つかりません"
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
        
        # セッション・ペイン存在確認
        if tmux has-session -t "$session" 2>/dev/null; then
            if tmux list-panes -t "$session:$window" -F "#{pane_index}" 2>/dev/null | grep -q "^$pane$"; then
                echo "✅ $agent : アクティブ"
                ((active_count++))
            else
                echo "⚠️  $agent : セッション存在、ペイン不明"
            fi
        else
            echo "❌ $agent : 未起動"
        fi
    done
    
    echo ""
    echo "アクティブ: $active_count / $total_count"
    
    # tmuxセッション情報
    echo ""
    echo "📺 tmuxセッション情報:"
    # アクティブなセッションをすべて表示
    tmux list-sessions 2>/dev/null | while IFS=: read -r session rest; do
        local pane_count=$(tmux list-panes -t "$session" 2>/dev/null | wc -l)
        echo "$session: $pane_count panes"
    done
}

# ブロードキャスト送信
broadcast_message() {
    local message="$1"
    local sent_count=0
    local failed_count=0
    
    echo "📢 ブロードキャスト送信開始: '$message'"
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
    echo "📊 ブロードキャスト結果:"
    echo "  成功: $sent_count"
    echo "  失敗: $failed_count"
    echo "  総計: $((sent_count + failed_count))"
}

# メッセージ送信
send_message() {
    local target="$1"
    local message="$2"
    local agent_name="$3"
    
    local session="${target%%:*}"
    local window_pane="${target##*:}"
    local window="${window_pane%%.*}"
    local pane="${window_pane##*.}"
    
    # セッション存在確認
    if ! tmux has-session -t "$session" 2>/dev/null; then
        echo "❌ $agent_name: セッション '$session' が見つかりません"
        return 1
    fi
    
    # ペイン存在確認
    if ! tmux list-panes -t "$session:$window" -F "#{pane_index}" 2>/dev/null | grep -q "^$pane$"; then
        echo "❌ $agent_name: ペイン '$pane' が見つかりません"
        return 1
    fi
    
    # メッセージ送信
    echo "📤 $agent_name ← '$message'"
    
    # メッセージ送信（クリア不要 - 新しい入力は自動的に置き換わる）
    tmux send-keys -t "$session:$window.$pane" "$message"
    sleep 0.1
    
    # エンター押下
    tmux send-keys -t "$session:$window.$pane" C-m
    sleep 0.3
    
    return 0
}

# ログ記録
log_message() {
    local agent="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    mkdir -p ./communication/logs
    echo "[$timestamp] $agent: \"$message\"" >> ./communication/logs/send_log.txt
}

# メイン処理
main() {
    # agent_and_pane_id_table.jsonl yükleme
    if ! load_agent_map; then
        exit 1
    fi
    
    # 引数チェック
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    # オプション処理
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
                echo "❌ ブロードキャスト用のメッセージが必要です"
                exit 1
            fi
            broadcast_message "$2"
            exit 0
            ;;
        *)
            if [[ $# -lt 2 ]]; then
                echo "❌ エージェント名とメッセージが必要です"
                show_usage
                exit 1
            fi
            ;;
    esac
    
    local agent_name="$1"
    local message="$2"
    
    # エージェント名を大文字に統一
    agent_name=$(echo "$agent_name" | tr '[:lower:]' '[:upper:]')
    
    # エージェントターゲット取得
    local target=$(get_agent_target "$agent_name")
    
    if [[ -z "$target" ]]; then
        echo "❌ エラー: 不明なエージェント '$agent_name'"
        echo "利用可能エージェント: $0 --list"
        exit 1
    fi
    
    # メッセージ送信
    if send_message "$target" "$message" "$agent_name"; then
        # ログ記録
        log_message "$agent_name" "$message"
        echo "✅ 送信完了: $aTamamlandı: $agent_name"
    else
        echo "❌ 送信失敗: $agent_name"
        exit 1
    fi
}

main "$@"
