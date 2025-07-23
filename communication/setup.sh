#!/bin/bash

# 🧬 OpenCodeAT Multi-Agent HPC Environment Setup
# Dynamic tmux session creation for user-specified agent count

set -e  # エラー時に停止

# 色付きログ関数
log_info() {
    echo -e "\033[1;32m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;34m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# 使用方法表示
show_usage() {
    cat << EOF
🧬 OpenCodeAT Multi-Agent HPC Environment Setup

使用方法:
  $0 [エージェント数(PM除く)] [オプション]

パラメータ:
  エージェント数  : SE, CI, PG, CD エージェントの総数 (推奨: 6-12)
  
オプション:
  --clean-only     : 既存セッションのクリーンアップのみ実行
  --dry-run        : 実際のセットアップを行わずに計画を表示
  --help           : このヘルプを表示

例:
  $0 11            # PM + 11エージェント構成でセットアップ
  $0 --clean-only  # クリーンアップのみ
  $0 --dry-run 11  # 11エージェント構成の計画表示

推奨構成 (1920x1280以上の画面解像度で推奨):
  6エージェント: PM(別) + SE(1) + CI(1) + PG(2) + CD(1) + 状態表示(1)
  8エージェント: PM(別) + SE(1) + CI(2) + PG(3) + CD(1) + 状態表示(1)
  10エージェント: PM(別) + SE(2) + CI(2) + PG(4) + CD(1) + 状態表示(1)
  12エージェント: PM(別) + SE(2) + CI(3) + PG(5) + CD(1) + 状態表示(1)
EOF
}

# エージェント構成計算
calculate_agent_distribution() {
    local total=$1  # PMを除いた数
    
    # 基本構成: CD(1) 固定
    local cd_count=1
    
    # 残りを SE, CI, PG に分配
    local remaining=$((total - cd_count))
    
    if [ $remaining -lt 5 ]; then
        log_error "エージェント数が少なすぎます。最小6エージェント(PM除く)必要です。"
        return 1
    fi
    
    # SE: 1-2, CI/PG: 残りを分配
    local se_count
    if [ $total -le 8 ]; then
        se_count=1
    else
        se_count=2
    fi
    
    local worker_count=$((remaining - se_count))
    local ci_count=$((worker_count / 2))
    local pg_count=$((worker_count - ci_count))
    
    echo "$se_count $ci_count $pg_count $cd_count"
}

# エージェント名生成（グループ化対応）
generate_agent_names() {
    local se_count=$1
    local ci_count=$2
    local pg_count=$3
    local cd_count=$4
    
    local agents=()
    
    # 左上に状態表示paneを追加
    agents+=("STATUS")
    
    # SE
    for ((i=1; i<=se_count; i++)); do
        agents+=("SE${i}")
    done
    
    # CI/PGをグループ化して配置
    local group_count
    if [ $ci_count -le 2 ]; then
        group_count=$ci_count
    else
        group_count=$(( (ci_count + 1) / 2 ))
    fi
    
    local ci_idx=1
    local pg_per_ci=$(( (pg_count + ci_count - 1) / ci_count ))
    
    for ((g=1; g<=group_count; g++)); do
        # CI
        for ((c=1; c<=2 && ci_idx<=ci_count; c++)); do
            if [ $ci_count -eq 1 ]; then
                agents+=("CI1")
                ci_idx=$((ci_idx + 1))
            else
                agents+=("CI1.$((ci_idx))")
                ci_idx=$((ci_idx + 1))
            fi
        done
    done
    
    # PG
    local pg_idx=1
    for ((g=1; g<=group_count && pg_idx<=pg_count; g++)); do
        for ((p=1; p<=pg_per_ci && pg_idx<=pg_count; p++)); do
            local ci_group=$((g))
            if [ $ci_count -eq 1 ]; then
                agents+=("PG1.1.$((pg_idx))")
            else
                agents+=("PG1.$((ci_group)).$((pg_idx))")
            fi
            pg_idx=$((pg_idx + 1))
        done
    done
    
    # CD
    agents+=("CD")
    
    echo "${agents[@]}"
}

# セッション重複チェックとリネーム
handle_existing_sessions() {
    log_info "🔍 既存セッションの確認とリネーム処理..."
    
    # pm_sessionの処理
    if tmux has-session -t pm_session 2>/dev/null; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local new_name="pm_session_old_${timestamp}"
        log_info "既存のpm_sessionを${new_name}にリネーム"
        tmux rename-session -t pm_session "${new_name}" 2>/dev/null || {
            log_error "pm_sessionのリネームに失敗。強制終了します"
            tmux kill-session -t pm_session 2>/dev/null || true
        }
    fi
    
    # opencodeatの処理
    if tmux has-session -t opencodeat 2>/dev/null; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local new_name="opencodeat_old_${timestamp}"
        log_info "既存のopencodeatを${new_name}にリネーム"
        tmux rename-session -t opencodeat "${new_name}" 2>/dev/null || {
            log_error "opencodeatのリネームに失敗。強制終了します"
            tmux kill-session -t opencodeat 2>/dev/null || true
        }
    fi
    
    # 古いmultiagentセッションがあれば削除
    tmux kill-session -t multiagent 2>/dev/null && log_info "古いmultiagentセッション削除"
    
    # ディレクトリ準備
    mkdir -p ./Agent-shared
    mkdir -p ./communication/logs
    mkdir -p ./tmp
    rm -f ./tmp/agent*_done.txt 2>/dev/null
    
    sleep 0.5
    log_success "✅ セッション準備完了"
}

# PMセッション作成
create_pm_session() {
    log_info "📺 PMセッション作成中..."
    
    # 新しいPMセッション作成（handle_existing_sessionsで既に処理済み）
    tmux new-session -d -s pm_session -n "project-manager"
    
    # セッションが作成されたか確認
    if ! tmux has-session -t pm_session 2>/dev/null; then
        log_error "pm_sessionの作成に失敗しました"
        log_info "既存のセッション一覧:"
        tmux list-sessions || echo "セッションなし"
        return 1
    fi
    
    tmux send-keys -t "pm_session:project-manager" "cd $(pwd)" C-m
    tmux send-keys -t "pm_session:project-manager" "export PS1='(\[\033[1;35m\]PM\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
    tmux send-keys -t "pm_session:project-manager" "clear" C-m
    tmux send-keys -t "pm_session:project-manager" "echo '=== PM (Project Manager) エージェント ==='" C-m
    tmux send-keys -t "pm_session:project-manager" "echo 'OpenCodeAT HPC最適化システム'" C-m
    tmux send-keys -t "pm_session:project-manager" "echo '役割: プロジェクト管理・要件定義'" C-m
    tmux send-keys -t "pm_session:project-manager" "echo ''" C-m
    tmux send-keys -t "pm_session:project-manager" "echo 'エージェント起動コマンド:'" C-m
    tmux send-keys -t "pm_session:project-manager" "echo 'claude --dangerously-skip-permissions'" C-m
    
    log_success "✅ PMセッション作成完了"
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
    echo "[OpenCodeAT エージェント配置図]"
    echo "================================"
    
    # エージェント配置を表示
    # TODO: 実際の配置に基づいて動的に生成
    
    sleep 5
done
EOF
    
    chmod +x "$script_file"
}

# メインエージェントセッション作成
create_main_session() {
    local total_agents=$1  # 状態表示pane含む
    local agents_str="$2"
    read -ra agents <<< "$agents_str"
    
    log_info "📺 メインエージェントセッション作成開始 (${total_agents}エージェント)..."
    
    # 固定レイアウト計算（状態表示pane含む）
    local cols rows
    if [ $total_agents -le 4 ]; then
        cols=2; rows=2
    elif [ $total_agents -le 9 ]; then
        cols=3; rows=3
    elif [ $total_agents -le 12 ]; then
        cols=3; rows=4
    elif [ $total_agents -le 16 ]; then
        cols=4; rows=4
    else
        cols=5; rows=4
    fi
    
    log_info "グリッド構成: ${cols}列 x ${rows}行"
    
    # セッションを作成（handle_existing_sessionsで既に処理済み）
    tmux new-session -d -s opencodeat -n "hpc-agents"
    
    # セッションが作成されたか確認
    if ! tmux has-session -t opencodeat 2>/dev/null; then
        log_error "opencodeatセッションの作成に失敗しました"
        return 1
    fi
    
    sleep 1
    
    # グリッド作成
    local pane_count=1
    
    # 最初の列を作成
    for ((j=1; j < rows && pane_count < total_agents; j++)); do
        tmux split-window -v -t "opencodeat:hpc-agents"
        ((pane_count++))
    done
    
    # 残りの列を作成
    for ((i=1; i < cols && pane_count < total_agents; i++)); do
        tmux select-pane -t "opencodeat:hpc-agents.0"
        tmux split-window -h -t "opencodeat:hpc-agents"
        ((pane_count++))
        
        for ((j=1; j < rows && pane_count < total_agents; j++)); do
            tmux split-window -v -t "opencodeat:hpc-agents"
            ((pane_count++))
        done
    done
    
    # レイアウト調整
    tmux select-layout -t "opencodeat:hpc-agents" tiled
    
    # エージェント設定
    local pane_indices=($(tmux list-panes -t "opencodeat:hpc-agents" -F "#{pane_index}"))
    
    for i in "${!pane_indices[@]}"; do
        if (( i >= ${#agents[@]} )); then break; fi
        
        local pane_index="${pane_indices[$i]}"
        local pane_target="opencodeat:hpc-agents.${pane_index}"
        local agent_name="${agents[$i]}"
        
        tmux select-pane -t "$pane_target" -T "$agent_name"
        tmux send-keys -t "$pane_target" "cd $(pwd)" C-m
        
        # エージェントタイプとグループで色分け
        local color_code
        if [ "$agent_name" = "STATUS" ]; then
            color_code="1;37"  # 白
        else
            case "${agent_name:0:2}" in
                "SE") color_code="1;36" ;;  # シアン
                "CI") 
                    # グループごとに色を変える
                    if [[ "$agent_name" =~ CI1\.1 ]]; then
                        color_code="1;33"  # 黄
                    else
                        color_code="1;93"  # 明るい黄
                    fi
                    ;;
                "PG") 
                    # CIグループと同じ色
                    if [[ "$agent_name" =~ PG1\.1\. ]]; then
                        color_code="1;32"  # 緑
                    else
                        color_code="1;92"  # 明るい緑
                    fi
                    ;;
                "CD") color_code="1;31" ;;  # 赤
                *) color_code="1;37" ;;     # 白
            esac
        fi
        
        tmux send-keys -t "$pane_target" "export PS1='(\[\033[${color_code}m\]${agent_name}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
        
        if [ "$agent_name" = "STATUS" ]; then
            tmux send-keys -t "$pane_target" "clear" C-m
            tmux send-keys -t "$pane_target" "echo '[OpenCodeAT エージェント配置状態]'" C-m
            tmux send-keys -t "$pane_target" "echo '================================'" C-m
            tmux send-keys -t "$pane_target" "./tmp/update_status_display.sh 2>/dev/null || echo '状態表示スクリプト準備中...'" C-m
        else
            tmux send-keys -t "$pane_target" "echo '=== ${agent_name} エージェント ==='" C-m
            
            local role
            case "${agent_name:0:2}" in
                "SE") role="システム設計・監視" ;;
                "CI") role="SSH・ビルド・実行" ;;
                "PG") role="コード生成・最適化" ;;
                "CD") role="GitHub・デプロイ管理" ;;
                *) role="専門エージェント" ;;
            esac
            
            tmux send-keys -t "$pane_target" "echo '役割: ${role}'" C-m
        fi
    done
    
    log_success "✅ メインエージェントセッション作成完了"
}

# agent_and_pane_id_table.txt生成
generate_agent_pane_table() {
    local agents=($1)
    local table_file="./Agent-shared/agent_and_pane_id_table.txt"
    
    log_info "📝 エージェント配置表生成中..."
    
    mkdir -p ./Agent-shared
    
    cat > "$table_file" << EOF
# OpenCodeAT Agent and Pane ID Table
# Generated: $(date)
# Format: AGENT_NAME: session=SESSION_NAME, window=WINDOW, pane=PANE_INDEX

PM: session=pm_session, window=0, pane=0
EOF
    
    # opencodeatセッションのエージェント
    local pane_indices=($(tmux list-panes -t "opencodeat:hpc-agents" -F "#{pane_index}" 2>/dev/null || echo ""))
    
    for i in "${!agents[@]}"; do
        if [ $i -lt ${#pane_indices[@]} ]; then
            echo "${agents[$i]}: session=opencodeat, window=0, pane=${pane_indices[$i]}" >> "$table_file"
        fi
    done
    
    log_success "✅ agent_and_pane_id_table.txt 生成完了"
}

# 実行計画表示
show_execution_plan() {
    local total_agents=$1
    local distribution=($2)
    local agents=($3)
    
    echo ""
    echo "📋 実行計画:"
    echo "============"
    echo "PMを除くエージェント数: $total_agents"
    echo "構成: PM(別セッション) + SE(${distribution[0]}) + CI(${distribution[1]}) + PG(${distribution[2]}) + CD(${distribution[3]}) + 状態表示(1)"
    echo ""
    echo "エージェント一覧:"
    echo "  PM (別セッション)"
    local i=1
    for agent in "${agents[@]}"; do
        printf "  %2d. %s\n" $i "$agent"
        ((i++))
    done
    echo ""
}

# メイン処理
main() {
    echo "🧬 OpenCodeAT Multi-Agent HPC Environment Setup"
    echo "==============================================="
    echo ""
    
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
        --clean-only)
            log_info "クリーンアップモード"
            # 古いセッションを完全に削除
            tmux kill-session -t opencodeat 2>/dev/null && log_info "opencodeatセッション削除"
            tmux kill-session -t pm_session 2>/dev/null && log_info "pm_sessionセッション削除"
            tmux list-sessions 2>/dev/null | grep -E "opencodeat_old_|pm_session_old_" | cut -d: -f1 | while read session; do
                tmux kill-session -t "$session" 2>/dev/null && log_info "${session}削除"
            done
            rm -rf ./tmp/agent*_done.txt 2>/dev/null
            log_success "✅ クリーンアップ完了"
            exit 0
            ;;
        --dry-run)
            if [[ $# -lt 2 ]]; then
                log_error "dry-runにはエージェント数が必要です"
                exit 1
            fi
            local total_agents=$2
            ;;
        *)
            if [[ ! "$1" =~ ^[0-9]+$ ]]; then
                log_error "エージェント数は数値で指定してください"
                exit 1
            fi
            local total_agents=$1
            ;;
    esac
    
    # エージェント数チェック（PMを除く）
    if [[ $total_agents -lt 6 || $total_agents -gt 20 ]]; then
        log_error "エージェント数は6-20の範囲で指定してください（PM除く）"
        exit 1
    fi
    
    # エージェント構成計算
    local distribution
    distribution=($(calculate_agent_distribution $total_agents))
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
    
    # エージェント名生成
    local agents
    agents=($(generate_agent_names "${distribution[@]}"))
    
    # 実行計画表示
    show_execution_plan $total_agents "${distribution[*]}" "${agents[*]}"
    
    # dry-runの場合はここで終了
    if [[ "$1" == "--dry-run" ]]; then
        log_info "dry-runモード: 実際のセットアップは行いません"
        exit 0
    fi
    
    # 既存セッションの確認とリネーム
    handle_existing_sessions
    
    # PMセッション作成
    create_pm_session
    
    # 状態表示スクリプト生成
    generate_status_display_script "${agents[*]}"
    
    # メインセッション作成（状態表示pane含む）
    local total_with_status=$((${#agents[@]}))
    create_main_session $total_with_status "${agents[*]}"
    
    # agent_and_pane_id_table.txt生成
    generate_agent_pane_table "${agents[*]}"
    
    # 完了メッセージ
    echo ""
    log_success "🎉 OpenCodeAT環境セットアップ完了！"
    echo ""
    echo "📋 次のステップ:"
    echo "  1. 🔗 セッションアタッチ:"
    echo "     # ターミナルタブ1: PM用"
    echo "     tmux attach-session -t pm_session"
    echo ""
    echo "     # ターミナルタブ2: その他のエージェント用"
    echo "     tmux attach-session -t opencodeat"
    echo ""
    echo "  2. 🤖 PM起動:"
    echo "     # pm_sessionで以下を実行:"
    echo "     claude --dangerously-skip-permissions"
    echo ""
    echo "  3. 📊 エージェント配置確認:"
    echo "     cat ./Agent-shared/agent_and_pane_id_table.txt"
    echo ""
    
    # セッション作成確認
    echo "🔍 セッション作成確認:"
    if tmux has-session -t pm_session 2>/dev/null; then
        echo "  ✅ pm_session: 作成成功"
    else
        echo "  ❌ pm_session: 作成失敗"
    fi
    
    if tmux has-session -t opencodeat 2>/dev/null; then
        echo "  ✅ opencodeat: 作成成功"
    else
        echo "  ❌ opencodeat: 作成失敗"
    fi
    
    echo ""
    echo "現在のtmuxセッション一覧:"
    tmux list-sessions || echo "セッションなし"
}

main "$@"