#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC PostToolUse Hook for SSH/SFTP Handler
ツール実行後にPID情報とセッション管理のアドバイスを提供
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def main():
    try:
        # JSONを読み込み
        input_data = json.load(sys.stdin)
        
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})
        
        # Desktop Commander MCPのstart_processの結果を処理
        if tool_name == "mcp__desktop-commander__start_process":
            command = tool_input.get("command", "")
            
            if command.startswith(("ssh ", "sftp ")):
                # PIDを抽出（tool_responseから）
                response_text = str(tool_response)
                pid = None
                
                # "Process started with PID XXXXX" パターンを探す
                import re
                pid_match = re.search(r'PID (\d+)', response_text)
                if pid_match:
                    pid = pid_match.group(1)
                
                if pid:
                    message = f"""
SSH/SFTPセッション開始を検出しました:
• PID: {pid}
• コマンド: {command}

【重要】以下の手順でセッション管理してください:
1. ssh_sftp_sessions.jsonを作成/更新してPID {pid}を記録
2. interact_with_processでコマンド実行（PID: {pid}）
3. セッション終了時はforce_terminate（PID: {pid}）

-ttオプションなしで接続した場合、インタラクティブ操作で問題が発生する可能性があります。
"""
                    
                    # stderrに出力して終了コード2でClaudeに表示
                    print(message, file=sys.stderr)
                    sys.exit(2)  # PostToolUseでは終了コード2でもClaudeに表示される
        
        # Bashツールで直接SSH/SFTP実行した場合
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            
            if command.strip().startswith(("ssh ", "sftp ", "scp ")):
                message = """
⚠️ Bashツールで直接SSH/SFTP/SCPを実行しました。

【推奨】Desktop Commander MCPを使用してください:
• /Agent-shared/ssh_sftp_guide.mdを参照
• セッション管理が可能
• 大量出力によるコンテキスト消費を防止
• 2段階認証の回避

次回からはmcp__desktop-commander__start_processの使用を検討してください。
"""
                
                # stderrに出力して終了コード2でClaudeに表示
                print(message, file=sys.stderr)
                sys.exit(2)  # PostToolUseでは終了コード2でもClaudeに表示される
        
        # その他の場合は何もしない
        sys.exit(0)
        
    except Exception as e:
        # エラーは静かに処理
        sys.exit(0)

if __name__ == "__main__":
    main()