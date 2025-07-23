#!/bin/bash

# CI wcgw設定支援スクリプト（SE用）
# SEがCIエージェントのwcgw MCPサーバ設定を支援するための専用ツール

# 使用方法表示
show_usage() {
    cat << EOF
🔧 CI wcgw設定支援スクリプト（SE用）

使用方法:
  $0 <CI_ID> <ACTION>

アクション:
  restart    : 指定したCIエージェントにexit→fgを送信
  check      : 指定したCIエージェントの状態確認
  batch      : 複数のCIエージェントを一括設定

例:
  $0 CI1.1 restart    # CI1.1を再起動
  $0 CI1.2 check      # CI1.2の状態確認
  $0 all batch        # 全CIエージェントを一括設定

注意:
- CIエージェントが事前にMCP設定を開始している必要があります
- exitコマンド送信後、3秒待機してからfgを送信します
EOF
}

# エージェントにコマンドを送信
send_to_agent() {
    local agent_id="$1"
    local command="$2"
    ./agent-send.sh "$agent_id" "$command"
}

# CIエージェントの再起動
restart_ci() {
    local ci_id="$1"
    echo "🔄 $ci_id を再起動します..."
    
    # exitコマンドを送信
    send_to_agent "$ci_id" "exit"
    echo "⏳ exitコマンドを送信しました。3秒待機..."
    sleep 3
    
    # fgコマンドを送信して復帰
    send_to_agent "$ci_id" "fg"
    echo "✅ fgコマンドを送信しました。"
    
    # 再起動完了
    echo "✅ $ci_id の再起動処理が完了しました。"
    echo "💡 CIエージェントはwcgwツールを認識しているはずです。"
}

# CIエージェントの状態確認
check_ci() {
    local ci_id="$1"
    echo "🔍 $ci_id の状態を確認します..."
    send_to_agent "$ci_id" "echo 'wcgw設定状態を確認してください'"
    echo "💡 CIエージェントに確認を促しました。"
}

# メイン処理
main() {
    if [[ $# -lt 2 ]]; then
        show_usage
        exit 1
    fi
    
    local ci_id="$1"
    local action="$2"
    
    case "$action" in
        restart)
            restart_ci "$ci_id"
            ;;
        check)
            check_ci "$ci_id"
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