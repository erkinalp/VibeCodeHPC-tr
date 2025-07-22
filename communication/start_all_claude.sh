#!/bin/bash

# 🧬 OpenCodeAT Claude Code一括起動スクリプト
# 全エージェントに対してclaudeコマンドを一括送信

# directory_map.txt読み込み
load_agent_map() {
    local map_file="./Agent-shared/directory_map.txt"
    
    if [[ ! -f "$map_file" ]]; then
        echo "❌ エラー: directory_map.txt が見つかりません"
        echo "./communication/setup.sh を実行済みでtmuxによる複数ターミナルが見えているかユーザに確認すること"
        echo "PMは Agent-shared/directory_map.txt を作成・更新する義務があります。PM.mdなどの必要書類に目を通しましたか?"
        return 1
    fi
    
    # associative array宣言
    declare -gA AGENT_MAP
    
    # directory_map.txt解析
    while IFS= read -r line; do
        # コメントと空行をスキップ
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # agent_name: session=xxx, pane=yyy 形式を解析
        if [[ "$line" =~ ^([^:]+):[[:space:]]*tmux_session=([^,]+),[[:space:]]*tmux_pane=(.+)$ ]]; then
            local agent_name="${BASH_REMATCH[1]// /}"
            local session="${BASH_REMATCH[2]// /}"
            local pane="${BASH_REMATCH[3]// /}"
            AGENT_MAP["$agent_name"]="$session:$pane"
        fi
    done < "$map_file"
}

# 使用方法表示
show_usage() {
    cat << EOF
🧬 OpenCodeAT Claude Code一括起動スクリプト

使用方法:
  $0 [オプション]

オプション:
  --sequential     : 順次起動（デフォルト: 並列）
  --delay N        : 起動間隔（秒、デフォルト: 0.5）
  --dry-run        : 実際の起動は行わず計画のみ表示
  --help           : このヘルプを表示

例:
  $0                      # 全エージェントを並列起動
  $0 --sequential         # 順次起動
  $0 --delay 2            # 2秒間隔で起動
  $0 --dry-run            # 起動計画のみ表示

注意:
  - 事前に ./communication/setup.sh でtmux環境を構築してください
  - Claude Codeの初回起動時はアカウント認証が必要な場合があります
  - PMエージェントには require_definition.md を渡してプロジェクトを開始してください
EOF
}

# Claude起動
start_claude() {
    local agent_name="$1"
    local target="$2"
    local delay="$3"
    
    local session="${target%%:*}"
    local pane="${target##*:}"
    
    echo "🚀 $agent_name: Claude Code起動中..."
    
    # 既存のプロセスを一度クリア
    tmux send-keys -t "$session:$pane" C-c 2>/dev/null
    sleep 0.2
    
    # claudeコマンド送信
    tmux send-keys -t "$session:$pane" "claude --dangerously-skip-permissions"
    sleep 0.1
    tmux send-keys -t "$session:$pane" C-m
    
    # 起動間隔
    if [[ "$delay" != "0" ]]; then
        sleep "$delay"
    fi
    
    return 0
}

# 順次起動
sequential_start() {
    local delay="$1"
    local success_count=0
    local total_count=${#AGENT_MAP[@]}
    
    echo "🔄 順次起動開始 (${total_count}エージェント, 間隔: ${delay}秒)"
    echo "=================================================="
    
    for agent in "${!AGENT_MAP[@]}"; do
        local target="${AGENT_MAP[$agent]}"
        local session="${target%%:*}"
        
        # セッション存在確認
        if tmux has-session -t "$session" 2>/dev/null; then
            start_claude "$agent" "$target" "$delay"
            ((success_count++))
        else
            echo "❌ $agent: セッション未起動"
        fi
    done
    
    echo ""
    echo "📊 起動結果:"
    echo "  成功: $success_count / $total_count"
    
    if [[ $success_count -eq $total_count ]]; then
        echo "✅ 全エージェント起動完了！"
    else
        echo "⚠️  一部エージェントの起動に失敗しました"
    fi
}

# 並列起動
parallel_start() {
    local delay="$1"
    local success_count=0
    local total_count=${#AGENT_MAP[@]}
    
    echo "⚡ 並列起動開始 (${total_count}エージェント, 間隔: ${delay}秒)"
    echo "=================================================="
    
    # 並列実行
    for agent in "${!AGENT_MAP[@]}"; do
        local target="${AGENT_MAP[$agent]}"
        local session="${target%%:*}"
        
        # セッション存在確認
        if tmux has-session -t "$session" 2>/dev/null; then
            start_claude "$agent" "$target" "0" &
            ((success_count++))
        else
            echo "❌ $agent: セッション未起動"
        fi
        
        # 間隔調整
        if [[ "$delay" != "0" ]]; then
            sleep "$delay"
        fi
    done
    
    # 全並列プロセス完了を待機
    wait
    
    echo ""
    echo "📊 起動結果:"
    echo "  成功: $success_count / $total_count"
    
    if [[ $success_count -eq $total_count ]]; then
        echo "✅ 全エージェント起動完了！"
    else
        echo "⚠️  一部エージェントの起動に失敗しました"
    fi
}

# 起動計画表示
show_plan() {
    echo "📋 Claude Code起動計画:"
    echo "=========================="
    echo "総エージェント数: ${#AGENT_MAP[@]}"
    echo ""
    
    local active_count=0
    
    for agent in "${!AGENT_MAP[@]}"; do
        local target="${AGENT_MAP[$agent]}"
        local session="${target%%:*}"
        
        if tmux has-session -t "$session" 2>/dev/null; then
            echo "✅ $agent → $target"
            ((active_count++))
        else
            echo "❌ $agent → $target (セッション未起動)"
        fi
    done
    
    echo ""
    echo "起動可能: $active_count / ${#AGENT_MAP[@]}"
    
    if [[ $active_count -eq 0 ]]; then
        echo ""
        echo "⚠️  起動可能なエージェントがありません"
        echo "先に ./communication/setup.sh を実行してください"
    fi
}

# メイン処理
main() {
    echo "🧬 OpenCodeAT Claude Code一括起動"
    echo "=================================="
    echo ""
    
    # directory_map.txt読み込み
    if ! load_agent_map; then
        exit 1
    fi
    
    # デフォルト設定
    local sequential=false
    local delay=0.5
    local dry_run=false
    
    # オプション処理
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sequential)
                sequential=true
                shift
                ;;
            --delay)
                if [[ $# -lt 2 ]]; then
                    echo "❌ --delayには数値が必要です"
                    exit 1
                fi
                delay="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                echo "❌ 不明なオプション: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # エージェント数チェック
    if [[ ${#AGENT_MAP[@]} -eq 0 ]]; then
        echo "❌ エージェントが見つかりません"
        echo "先に ./communication/setup.sh を実行してください"
        exit 1
    fi
    
    # dry-runの場合
    if [[ "$dry_run" == true ]]; then
        show_plan
        exit 0
    fi
    
    # 起動実行
    if [[ "$sequential" == true ]]; then
        sequential_start "$delay"
    else
        parallel_start "$delay"
    fi
    
    echo ""
    echo "📋 次のステップ:"
    echo "  1. 🔍 エージェント状態確認:"
    echo "     ./communication/agent-send.sh --status"
    echo ""
    echo "  2. 📺 tmux画面確認:"
    echo "     tmux attach-session -t opencodeat"
    echo ""
    echo "  3. 🎯 プロジェクト開始:"
    echo "     ./communication/agent-send.sh PM \"requirement_definition.mdに基づいてプロジェクトを初期化してください\""
    echo ""
    echo "  4. 📊 リアルタイム監視:"
    echo "     watch -n 5 './communication/agent-send.sh --status'"
    echo ""
}

main "$@"