#!/bin/bash

# エージェント再起動支援スクリプト（MCP設定後用）
# MCPサーバ設定後のエージェント再起動を支援する汎用ツール

# 使用方法表示
show_usage() {
    cat << EOF
🔧 エージェント再起動支援スクリプト（MCP設定後用）

使用方法:
  $0 <AGENT_ID> <ACTION>

アクション:
  restart    : 指定したエージェントにexit→claude --continue --dangerously-skip-permissionsを送信
  check      : 指定したエージェントの状態確認
  batch      : 複数のエージェントを一括設定

例:
  $0 CI1.1 restart    # CI1.1を再起動
  $0 SE1 check        # SE1の状態確認
  $0 all batch        # 全エージェントを一括設定

注意:
- エージェントが事前にMCP設定を開始している必要があります
- exitコマンド送信後、3秒待機してからclaude --continue --dangerously-skip-permissionsを送信します
EOF
}

# エージェントにコマンドを送信
send_to_agent() {
    local agent_id="$1"
    local command="$2"
    ./agent-send.sh "$agent_id" "$command"
}

# エージェントの再起動
restart_agent() {
    local agent_id="$1"
    echo "🔄 $agent_id を再起動します..."
    
    # exitコマンドを送信
    send_to_agent "$agent_id" "exit"
    echo "⏳ exitコマンドを送信しました。3秒待機..."
    sleep 3
    
    # claude --continue --dangerously-skip-permissionsコマンドを送信して復帰
    send_to_agent "$agent_id" "claude --continue --dangerously-skip-permissions"
    echo "✅ claude --continue --dangerously-skip-permissionsコマンドを送信しました。"
    
    # 再起動完了
    echo "✅ $agent_id の再起動処理が完了しました。"
    echo "💡 エージェントはMCPツールを認識しているはずです。"
}

# エージェントの状態確認
check_agent() {
    local agent_id="$1"
    echo "🔍 $agent_id の状態を確認します..."
    send_to_agent "$agent_id" "echo 'MCP設定状態を確認してください'"
    echo "💡 エージェントに確認を促しました。"
}

# メイン処理
main() {
    if [[ $# -lt 2 ]]; then
        show_usage
        exit 1
    fi
    
    local agent_id="$1"
    local action="$2"
    
    case "$action" in
        restart)
            restart_agent "$agent_id"
            ;;
        check)
            check_agent "$agent_id"
            ;;
        batch)
            echo "⚠️  バッチ処理は未実装です"
            ;;
        *)
            echo "❌ 不明なアクション: $action"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"