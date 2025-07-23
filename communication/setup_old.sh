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
  $0 [エージェント総数] [オプション]

パラメータ:
  エージェント総数  : PM, SE, CI, PG, CD エージェントの総数 (推奨: 6-12)
  
オプション:
  --clean-only     : 既存セッションのクリーンアップのみ実行
  --dry-run        : 実際のセットアップを行わずに計画を表示
  --help           : このヘルプを表示

例:
  $0 8             # 8エージェント構成でセットアップ
  $0 10            # 10エージェント構成でセットアップ
  $0 --clean-only  # クリーンアップのみ
  $0 --dry-run 8   # 8エージェント構成の計画表示

推奨構成 (1920x1280以上の画面解像度で推奨):
  6エージェント: PM(1) + SE(1) + CI(1) + PG(2) + CD(1)
  8エージェント: PM(1) + SE(1) + CI(2) + PG(3) + CD(1)
  10エージェント: PM(1) + SE(2) + CI(2) + PG(4) + CD(1)
  12エージェント: PM(1) + SE(2) + CI(3) + PG(5) + CD(1)
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

# エージェント名生成
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
    
    # CIとPGをグループ化して配置
    # TODO: より詳細なグループ化ロジックが必要
    for ((i=1; i<=ci_count; i++)); do
        agents+=("CI${i}")
    done
    
    for ((i=1; i<=pg_count; i++)); do
        agents+=("PG${i}")
    done
    
    # CD
    for ((i=1; i<=cd_count; i++)); do
        agents+=("CD")
    done
    
    echo "${agents[@]}"
}

# 既存セッションクリーンアップ
cleanup_sessions() {
    log_info "🧹 既存セッションクリーンアップ開始..."
    
    # OpenCodeAT関連セッション削除
    tmux kill-session -t opencodeat 2>/dev/null && log_info "opencodeatセッション削除完了" || log_info "opencodeatセッションは存在しませんでした"
    tmux kill-session -t pm_session 2>/dev/null && log_info "pm_sessionセッション削除完了" || log_info "pm_sessionセッションは存在しませんでした"
    
    # 古いセッション削除
    tmux kill-session -t multiagent 2>/dev/null && log_info "multiagentセッション削除完了" || log_info "multiagentセッションは存在しませんでした"
    tmux kill-session -t president 2>/dev/null && log_info "presidentセッション削除完了" || log_info "presidentセッションは存在しませんでした"
    
    # 一時ファイルクリア
    mkdir -p ./tmp
    rm -f ./tmp/agent*_done.txt 2>/dev/null && log_info "既存の完了ファイルをクリア" || log_info "完了ファイルは存在しませんでした"
    
    # ログディレクトリ作成
    mkdir -p ./communication/logs
    
    log_success "✅ クリーンアップ完了"
}

# tmuxセッション作成
create_tmux_session() {
    local total_agents=$1
    local agents_str="$2"
    read -ra agents <<< "$agents_str"

    log_info "📺 OpenCodeAT tmuxセッション作成開始 (${total_agents}エージェント)..."

    # ★★対策：最適な行と列の数を計算★★
    local cols=$(echo "sqrt($total_agents)" | bc)
    if (( cols * cols < total_agents )); then
        cols=$((cols + 1))
    fi
    local rows=$(echo "($total_agents + $cols - 1) / $cols" | bc)
    log_info "グリッド構成を計算: ${cols}列 x ${rows}行"

    # セッションを作成
    tmux new-session -d -s opencodeat -n "hpc-agents"
    log_info "サーバー起動待機中..."
    sleep 1

    # 最初のペイン（左上）は作成済み
    local pane_count=1

    # ★★対策：グリッドを論理的に作成★★
    # 1. 最初の「列」を作成 (行を分割)
    for ((j=1; j < rows && pane_count < total_agents; j++)); do
        tmux split-window -v
        sleep 0.2
        ((pane_count++))
    done

    # 2. 残りの「列」を右側に追加していく
    for ((i=1; i < cols && pane_count < total_agents; i++)); do
        # 最初の列の一番上のペインを選択して、右に分割（新しい列を作る）
        tmux select-pane -t ".0"
        tmux split-window -h
        sleep 0.2
        ((pane_count++))
        
        # 新しくできた列をさらに下に分割
        for ((j=1; j < rows && pane_count < total_agents; j++)); do
            tmux split-window -v
            sleep 0.2
            ((pane_count++))
        done
    done

    # 最後にレイアウトを整える
    tmux select-layout tiled
    log_info "ペイン作成完了。エージェント設定中..."
    sleep 0.5

    # --- ここから下の処理は変更不要 ---
    local pane_indices=($(tmux list-panes -t "opencodeat:hpc-agents" -F "#{pane_index}"))

    for i in "${!pane_indices[@]}"; do
        if (( i >= total_agents )); then break; fi
        local pane_index="${pane_indices[$i]}"
        local pane_target="opencodeat:hpc-agents.${pane_index}"
        local agent_name="${agents[$i]}"
        
        tmux select-pane -t "$pane_target" -T "$agent_name"
        tmux send-keys -t "$pane_target" "cd $(pwd)" C-m
        
        local color_code
        case "${agent_name:0:2}" in
            "PM") color_code="1;35" ;; "SE") color_code="1;36" ;; "CI") color_code="1;33" ;;
            "PG") color_code="1;32" ;; "CD") color_code="1;31" ;; *) color_code="1;37" ;;
        esac
        
        tmux send-keys -t "$pane_target" "export PS1='(\[\033[${color_code}m\]${agent_name}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
        tmux send-keys -t "$pane_target" "echo '=== ${agent_name} エージェント ==='" C-m
        
        local role
        case "${agent_name:0:2}" in
            "PM") role="プロジェクト管理・要件定義" ;; "SE") role="システム設計・監視" ;; "CI") role="SSH・ビルド・実行" ;;
            "PG") role="コード生成・最適化" ;; "CD") role="GitHub・デプロイ管理" ;; *) role="専門エージェント" ;;
        esac
        
        tmux send-keys -t "$pane_target" "echo '役割: ${role}'" C-m
    done
    
    log_success "✅ OpenCodeAT tmuxセッション作成完了"
}


# 設定ファイル生成
generate_config_files() {
    local total_agents=$1
    local agents=($2)
    
    log_info "📝 設定ファイル生成中..."
    
    # directory_map.txt更新
    local map_file="./Agent-shared/directory_map.txt"
    echo "# OpenCodeAT Agent Directory Map" > "$map_file"
    echo "# Generated: $(date)" >> "$map_file"
    echo "# Total Agents: $total_agents" >> "$map_file"
    echo "" >> "$map_file"
    
    for agent in "${agents[@]}"; do
        echo "$agent: tmux_session=opencodeat, tmux_pane=$agent" >> "$map_file"
    done
    
    log_success "✅ 設定ファイル生成完了"
}

# 実行計画表示
show_execution_plan() {
    local total_agents=$1
    local distribution=($2)
    local agents=($3)
    
    echo ""
    echo "📋 実行計画:"
    echo "============"
    echo "総エージェント数: $total_agents"
    echo "構成: PM(${distribution[0]}) + SE(${distribution[1]}) + CI(${distribution[2]}) + PG(${distribution[3]}) + CD(${distribution[4]})"
    echo ""
    echo "エージェント一覧:"
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
            cleanup_sessions
            exit 0
            ;;
        --dry-run)
            if [[ $# -lt 2 ]]; then
                log_error "dry-runにはエージェント総数が必要です"
                exit 1
            fi
            local total_agents=$2
            ;;
        *)
            if [[ ! "$1" =~ ^[0-9]+$ ]]; then
                log_error "エージェント総数は数値で指定してください"
                exit 1
            fi
            local total_agents=$1
            ;;
    esac
    
    # エージェント総数チェック
    if [[ $total_agents -lt 8 || $total_agents -gt 36 ]]; then
        log_error "エージェント総数は8-36の範囲で指定してください"
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
    
    # クリーンアップ
    cleanup_sessions
    
    # tmuxセッション作成
    create_tmux_session $total_agents "${agents[*]}"
    
    # 設定ファイル生成
    generate_config_files $total_agents "${agents[*]}"
    
    # 完了メッセージ
    echo ""
    log_success "🎉 OpenCodeAT環境セットアップ完了！"
    echo ""
    echo "📋 次のステップ:"
    echo "  1. 🔗 セッションアタッチ:"
    echo "     tmux attach-session -t opencodeat"
    echo ""
    echo "  2. 🤖 Claude Code一括起動:"
    echo "     ./communication/start_all_claude.sh"
    echo ""
    echo "  3. 📜 エージェント指示書:"
    echo "     PM: instructions/PM.md"
    echo "     SE: instructions/SE.md"
    echo "     CI: instructions/CI.md"
    echo "     PG: instructions/PG.md"
    echo "     CD: instructions/CD.md"
    echo ""
    echo "  4. 🎯 プロジェクト開始:"
    echo "     PMに requirement_definition.md を渡してプロジェクト初期化"
    echo ""
    echo "  5. 📊 監視:"
    echo "     tmux capture-pane -t opencodeat -p  # 全エージェント状態確認"
    echo ""
}

main "$@"