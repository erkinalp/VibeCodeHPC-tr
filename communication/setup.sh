#!/bin/bash

# 🧬 VibeCodeHPC Multi-Agent HPC Environment Setup
# Dynamic tmux session creation for user-specified agent count

set -e  # エラー時に停止

# プロジェクトルートの取得（setup.shの親ディレクトリ）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# グローバル変数
PROJECT_NAME=""  # ユーザが指定するプロジェクト名
USE_DEFAULT_NAMES=true  # デフォルト名使用フラグ
DRY_RUN=false  # dry-runフラグ

# デフォルトセッション名
DEFAULT_PM_SESSION="Team1_PM"
DEFAULT_WORKER_SESSION="Team1_Workers1"
DEFAULT_WORKER_SESSION_PREFIX="Team1_Workers"  # 13体以上の場合用

# 実際に使用するセッション名（determine_session_namesで設定）
PM_SESSION=""
WORKER_SESSION=""
WORKER_SESSION_PREFIX=""

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
🧬 VibeCodeHPC Multi-Agent HPC Environment Setup

使用方法:
  $0 [ワーカー数(PM除く)] [オプション]

パラメータ:
  ワーカー数      : PM以外のエージェント総数 (最小: 3)
  
オプション:
  --project <名前>  : プロジェクト名を指定（例: GEMM, MatMul）
  --clean-only     : 既存セッションのクリーンアップのみ実行
  --dry-run        : 実際のセットアップを行わずに計画を表示
  --help           : このヘルプを表示

例:
  $0 11                    # デフォルト名 (Team1_PM, Team1_Workers1)
  $0 11 --project GEMM     # プロジェクト名指定 (GEMM_PM, GEMM_Workers1)
  $0 --clean-only          # クリーンアップのみ
  $0 --dry-run 11          # 11ワーカー構成の計画表示

セッション名の命名規則:
  デフォルト: Team1_PM, Team1_Workers1, Team1_Workers2...
  プロジェクト指定: <ProjectName>_PM, <ProjectName>_Workers1...

参考構成例（実際の配置はPMが決定）:
  3人: SE(1) + CI(1) + PG(1) ※最小構成
  6人: SE(1) + CI(1) + PG(3) + CD(1)
  8人: SE(2) + CI(2) + PG(3) + CD(1)
  11人: SE(2) + CI(2) + PG(6) + CD(1)
  15人: SE(2) + CI(3) + PG(9) + CD(1)
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
    
    log_info "🔍 セッション名の衝突チェック中..."
    
    # PMセッションのチェック
    if tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        log_error "❌ セッション '$PM_SESSION' は既に存在します"
        conflicts=true
    fi
    
    # ワーカーセッションのチェック
    if tmux has-session -t "$WORKER_SESSION" 2>/dev/null; then
        log_error "❌ セッション '$WORKER_SESSION' は既に存在します"
        conflicts=true
    fi
    
    if [ "$conflicts" = true ]; then
        echo ""
        echo "既存のセッション一覧:"
        tmux list-sessions 2>/dev/null || echo "セッションなし"
        echo ""
        echo "対処方法:"
        echo "1. 別のプロジェクト名を指定: $0 $1 --project <別の名前>"
        echo "2. 既存セッションを削除: tmux kill-session -t $PM_SESSION"
        echo "3. --clean-only オプションで古いセッションをクリーンアップ"
        return 1
    fi
    
    log_success "✅ セッション名の衝突なし"
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
    log_success "✅ セッション準備完了"
}

# PMセッション作成
create_pm_session() {
    log_info "📺 PMセッション作成中: $PM_SESSION"
    
    # 新しいPMセッション作成
    tmux new-session -d -s "$PM_SESSION" -n "project-manager"
    
    # セッションが作成されたか確認
    if ! tmux has-session -t "$PM_SESSION" 2>/dev/null; then
        log_error "${PM_SESSION}の作成に失敗しました"
        log_info "既存のセッション一覧:"
        tmux list-sessions || echo "セッションなし"
        return 1
    fi
    
    tmux send-keys -t "${PM_SESSION}:project-manager" "cd $PROJECT_ROOT" C-m
    # bash/zsh対応プロンプト設定
    tmux send-keys -t "${PM_SESSION}:project-manager" "if [ -n \"\$ZSH_VERSION\" ]; then" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "  export PROMPT=$'%{\033[1;35m%}(PM)%{\033[0m%} %{\033[1;32m%}%~%{\033[0m%}$ '" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "elif [ -n \"\$BASH_VERSION\" ]; then" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "  export PS1='(\[\033[1;35m\]PM\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "fi" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "clear" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo '=== PM (Project Manager) エージェント ==='" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo 'VibeCodeHPC HPC最適化システム'" C-m
    if [ -n "$PROJECT_NAME" ] && [ "$USE_DEFAULT_NAMES" = false ]; then
        tmux send-keys -t "${PM_SESSION}:project-manager" "echo 'プロジェクト: ${PROJECT_NAME}'" C-m
    fi
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo '役割: プロジェクト管理・要件定義'" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo ''" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo 'エージェント起動コマンド:'" C-m
    tmux send-keys -t "${PM_SESSION}:project-manager" "echo './start_PM.sh'" C-m
    
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
    echo "[VibeCodeHPC エージェント配置図]"
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
    local total_panes=$1  # ユーザ入力数 + 1 (STATUS用)
    
    log_info "📺 メインエージェントセッション作成開始: $WORKER_SESSION (${total_panes}ペイン)..."
    
    # 固定レイアウト計算
    local cols rows
    if [ $total_panes -le 4 ]; then
        cols=2; rows=2
    elif [ $total_panes -le 9 ]; then
        cols=3; rows=3
    elif [ $total_panes -le 12 ]; then
        cols=3; rows=4
    elif [ $total_panes -le 16 ]; then
        cols=4; rows=4
    else
        cols=5; rows=4
    fi
    
    log_info "グリッド構成: ${cols}列 x ${rows}行"
    
    # セッションを作成
    tmux new-session -d -s "$WORKER_SESSION" -n "hpc-agents"
    
    # セッションが作成されたか確認
    if ! tmux has-session -t "$WORKER_SESSION" 2>/dev/null; then
        log_error "${WORKER_SESSION}セッションの作成に失敗しました"
        return 1
    fi
    
    sleep 1
    
    # グリッド作成
    local pane_count=1
    
    # 最初の列を作成
    for ((j=1; j < rows && pane_count < total_panes; j++)); do
        tmux split-window -v -t "${WORKER_SESSION}:hpc-agents"
        ((pane_count++))
    done
    
    # 残りの列を作成
    for ((i=1; i < cols && pane_count < total_panes; i++)); do
        tmux select-pane -t "${WORKER_SESSION}:hpc-agents.0"
        tmux split-window -h -t "${WORKER_SESSION}:hpc-agents"
        ((pane_count++))
        
        for ((j=1; j < rows && pane_count < total_panes; j++)); do
            tmux split-window -v -t "${WORKER_SESSION}:hpc-agents"
            ((pane_count++))
        done
    done
    
    # レイアウト調整
    tmux select-layout -t "${WORKER_SESSION}:hpc-agents" tiled
    
    # 全ペインの初期化
    local pane_indices=($(tmux list-panes -t "${WORKER_SESSION}:hpc-agents" -F "#{pane_index}"))
    
    for i in "${!pane_indices[@]}"; do
        local pane_index="${pane_indices[$i]}"
        local pane_target="${WORKER_SESSION}:hpc-agents.${pane_index}"
        
        tmux send-keys -t "$pane_target" "cd $PROJECT_ROOT" C-m
        
        # OpenTelemetry環境変数を設定（全ペイン共通）
        tmux send-keys -t "$pane_target" "export CLAUDE_CODE_ENABLE_TELEMETRY=1" C-m
        tmux send-keys -t "$pane_target" "export OTEL_METRICS_EXPORTER=otlp" C-m
        tmux send-keys -t "$pane_target" "export OTEL_METRIC_EXPORT_INTERVAL=10000" C-m
        tmux send-keys -t "$pane_target" "export OTEL_LOGS_EXPORTER=otlp" C-m
        tmux send-keys -t "$pane_target" "export OTEL_LOG_USER_PROMPTS=0" C-m
        tmux send-keys -t "$pane_target" "export OTEL_EXPORTER_OTLP_PROTOCOL=grpc" C-m
        tmux send-keys -t "$pane_target" "export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317" C-m
        
        if [ $i -eq 0 ]; then
            # 最初のペインはSTATUS用
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
            tmux send-keys -t "$pane_target" "echo 'ワーカー数: $((total_panes - 1))'" C-m
            tmux send-keys -t "$pane_target" "echo 'Agent-shared/directory_map.txt を参照してください'" C-m
        else
            # その他のペインはエージェント配置待ち
            local pane_number=$i
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
            tmux send-keys -t "$pane_target" "echo 'PMがdirectory_map.txtで配置を決定します'" C-m
            tmux send-keys -t "$pane_target" "echo 'その後、エージェントが起動されます'" C-m
            tmux send-keys -t "$pane_target" "echo ''" C-m
            tmux send-keys -t "$pane_target" "echo '📊 OpenTelemetryが有効化されています'" C-m
            tmux send-keys -t "$pane_target" "echo '   OTLP エンドポイント: http://localhost:4317'" C-m
        fi
    done
    
    log_success "✅ メインエージェントセッション作成完了"
}

# agent_and_pane_id_table生成（初期状態）
generate_agent_pane_table() {
    local total_panes=$1
    
    local jsonl_table_file="./Agent-shared/agent_and_pane_id_table.jsonl"
    
    log_info "📝 エージェント配置表（初期状態）生成中..."
    
    mkdir -p ./Agent-shared
    
    # JSONL形式のファイル（コメントなしのピュアなJSONL）
    > "$jsonl_table_file"
    
    # PMエントリ（working_dirは空文字列で初期化）
    echo '{"agent_id": "PM", "tmux_session": "'$PM_SESSION'", "tmux_window": 0, "tmux_pane": 0, "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
    
    # ワーカーセッションのペイン（初期状態）
    local pane_indices=($(tmux list-panes -t "${WORKER_SESSION}:hpc-agents" -F "#{pane_index}" 2>/dev/null || echo ""))
    
    for i in "${!pane_indices[@]}"; do
        local pane_id="${pane_indices[$i]}"
        local agent_id
        if [ $i -eq 0 ]; then
            agent_id="STATUS"
        else
            agent_id="待機中${i}"
        fi
        echo '{"agent_id": "'$agent_id'", "tmux_session": "'$WORKER_SESSION'", "tmux_window": 0, "tmux_pane": '$pane_id', "working_dir": "", "claude_session_id": null, "status": "not_started", "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> "$jsonl_table_file"
    done
    
    log_success "✅ agent_and_pane_id_table.jsonl 生成完了"
}

# 実行計画表示（シンプル版）
show_execution_plan() {
    local worker_count=$1
    
    echo ""
    echo "📋 セットアップ情報:"
    echo "===================="
    echo "ワーカー数: $worker_count (PM除く)"
    echo "ペイン数: $((worker_count + 1)) (STATUS含む)"
    echo ""
    echo "参考構成例（実際の配置はPMが決定）:"
    echo "  3人: SE(1) + CI(1) + PG(1) ※最小構成"
    echo "  6人: SE(1) + CI(1) + PG(3) + CD(1)"
    echo "  8人: SE(2) + CI(2) + PG(3) + CD(1)"
    echo "  11人: SE(2) + CI(2) + PG(6) + CD(1)"
    echo "  15人: SE(2) + CI(3) + PG(9) + CD(1)"
    echo ""
    echo "推奨: SEは2人が理想的、CIとPGはプロジェクトの特性に応じて調整"
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
    
    # エージェント数チェック（PMを除く、最小構成: SE + CI + PG = 3）
    if [[ $worker_count -lt 3 ]]; then
        log_error "エージェント数は3以上を指定してください（PM除く、最小構成: SE + CI + PG）"
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
    
    # PMセッション作成
    create_pm_session
    
    # メインセッション作成（ワーカー数 + STATUS用）
    local total_panes=$((worker_count + 1))
    create_main_session $total_panes
    
    # agent_and_pane_id_table.jsonl生成（初期状態）
    generate_agent_pane_table $total_panes
    
    # 完了メッセージ
    echo ""
    log_success "🎉 VibeCodeHPC環境セットアップ完了！"
    echo ""
    echo "📋 次のステップ:"
    echo "  1. 🔗 セッションアタッチ:"
    echo "     # ターミナルタブ1: PM用"
    echo "     tmux attach-session -t $PM_SESSION"
    echo ""
    echo "     # ターミナルタブ2: その他のエージェント用"
    echo "     tmux attach-session -t $WORKER_SESSION"
    echo ""
    echo "  2. 🤖 PM起動:"
    echo "     # $PM_SESSION で以下を実行:"
    echo "     ./start_PM.sh"
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
    
    if tmux has-session -t "$WORKER_SESSION" 2>/dev/null; then
        echo "  ✅ $WORKER_SESSION: 作成成功"
    else
        echo "  ❌ $WORKER_SESSION: 作成失敗"
    fi
    
    echo ""
    echo "現在のtmuxセッション一覧:"
    tmux list-sessions || echo "セッションなし"
}

main "$@"