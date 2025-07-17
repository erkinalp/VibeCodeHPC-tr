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
  エージェント総数  : PM, SE, CI, PG, CD エージェントの総数 (例: 12, 16)
  
オプション:
  --clean-only     : 既存セッションのクリーンアップのみ実行
  --dry-run        : 実際のセットアップを行わずに計画を表示
  --help           : このヘルプを表示

例:
  $0 12            # 12エージェント構成でセットアップ
  $0 16            # 16エージェント構成でセットアップ
  $0 --clean-only  # クリーンアップのみ
  $0 --dry-run 12  # 12エージェント構成の計画表示

推奨構成:
  12エージェント: PM(1) + SE(2) + CI(3) + PG(5) + CD(1)
  16エージェント: PM(1) + SE(2) + CI(4) + PG(8) + CD(1)
EOF
}

# エージェント構成計算
calculate_agent_distribution() {
    local total=$1
    
    # 基本構成: PM(1) + CD(1) = 2 (固定)
    local pm_count=1
    local cd_count=1
    local fixed_count=$((pm_count + cd_count))
    
    # 残りを SE, CI, PG に分配
    local remaining=$((total - fixed_count))
    
    if [ $remaining -lt 6 ]; then
        log_error "エージェント総数が少なすぎます。最小8エージェント必要です。"
        return 1
    fi
    
    # SE: 2固定、CI/PG: 残りを等分
    local se_count=2
    local worker_count=$((remaining - se_count))
    local ci_count=$((worker_count / 2))
    local pg_count=$((worker_count - ci_count))
    
    echo "$pm_count $se_count $ci_count $pg_count $cd_count"
}

# エージェント名生成
generate_agent_names() {
    local pm_count=$1
    local se_count=$2
    local ci_count=$3
    local pg_count=$4
    local cd_count=$5
    
    local agents=()
    
    # PM
    for ((i=1; i<=pm_count; i++)); do
        agents+=("PM")
    done
    
    # SE
    for ((i=1; i<=se_count; i++)); do
        agents+=("SE${i}")
    done
    
    # CI
    for ((i=1; i<=ci_count; i++)); do
        agents+=("CI${i}")
    done
    
    # PG
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
    local agents=($2)
    
    log_info "📺 OpenCodeAT tmuxセッション作成開始 (${total_agents}エージェント)..."
    
    # メインセッション作成
    tmux new-session -d -s opencodeat -n "hpc-agents"
    
    # セッション作成確認
    if ! tmux has-session -t opencodeat 2>/dev/null; then
        log_error "opencodeatセッションの作成に失敗しました"
        return 1
    fi
    
    # 最適なグリッド計算
    local cols rows
    if [ $total_agents -le 4 ]; then
        cols=2; rows=2
    elif [ $total_agents -le 9 ]; then
        cols=3; rows=3
    elif [ $total_agents -le 16 ]; then
        cols=4; rows=4
    elif [ $total_agents -le 25 ]; then
        cols=5; rows=5
    else
        cols=6; rows=6
    fi
    
    log_info "グリッド構成: ${cols}x${rows} (${total_agents}エージェント)"
    
    # 最初のペインはすでに存在するので、残りを作成
    local panes_needed=$((total_agents - 1))
    local current_panes=1
    
    # 水平分割で列を作成
    for ((col=1; col<cols && current_panes<total_agents; col++)); do
        tmux split-window -h -t "opencodeat:hpc-agents"
        ((current_panes++))
    done
    
    # 各列を垂直分割で行を作成
    for ((col=0; col<cols && current_panes<total_agents; col++)); do
        for ((row=1; row<rows && current_panes<total_agents; row++)); do
            # 該当する列の最初のペインを選択
            tmux select-pane -t "opencodeat:hpc-agents.${col}"
            tmux split-window -v
            ((current_panes++))
        done
    done
    
    # ペイン配置の確認
    local actual_panes=$(tmux list-panes -t "opencodeat:hpc-agents" | wc -l)
    log_info "作成されたペイン数: $actual_panes / $total_agents"
    
    # エージェント配置
    local pane_ids=($(tmux list-panes -t "opencodeat:hpc-agents" -F "#{pane_id}"))
    
    for ((i=0; i<total_agents; i++)); do
        if [ $i -lt ${#pane_ids[@]} ]; then
            local pane_id="${pane_ids[$i]}"
            local agent_name="${agents[$i]}"
            
            # ペインタイトル設定
            tmux select-pane -t "$pane_id" -T "$agent_name"
            
            # 作業ディレクトリ設定
            tmux send-keys -t "$pane_id" "cd $(pwd)" C-m
            
            # エージェント別カラープロンプト
            local color_code
            case "${agent_name:0:2}" in
                "PM") color_code="1;35" ;;  # マゼンタ
                "SE") color_code="1;36" ;;  # シアン
                "CI") color_code="1;33" ;;  # イエロー
                "PG") color_code="1;32" ;;  # グリーン
                "CD") color_code="1;31" ;;  # レッド
                *) color_code="1;37" ;;     # ホワイト
            esac
            
            tmux send-keys -t "$pane_id" "export PS1='(\[\033[${color_code}m\]${agent_name}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
            
            # ウェルカムメッセージ
            tmux send-keys -t "$pane_id" "echo '=== ${agent_name} エージェント ==='" C-m
            tmux send-keys -t "$pane_id" "echo 'OpenCodeAT HPC最適化システム'" C-m
            
            # 役割表示
            local role
            case "${agent_name:0:2}" in
                "PM") role="プロジェクト管理・要件定義" ;;
                "SE") role="システム設計・監視" ;;
                "CI") role="SSH・ビルド・実行" ;;
                "PG") role="コード生成・最適化" ;;
                "CD") role="GitHub・デプロイ管理" ;;
                *) role="専門エージェント" ;;
            esac
            
            tmux send-keys -t "$pane_id" "echo '役割: ${role}'" C-m
        fi
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