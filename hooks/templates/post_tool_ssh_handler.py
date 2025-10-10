#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC PostToolUse Hook for SSH/SFTP Handler
ツールYürütme後にPID情報とセッションYönetimのアドバイスを提供
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def check_ssh_sessions_file():
    """ssh_sftp_sessions.jsonの存在Kontrol"""
    sessions_file = Path.cwd() / "ssh_sftp_sessions.json"
    if sessions_file.exists():
        try:
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)
                return len(sessions.get("sessions", [])) > 0
        except:
            return False
    return False

def main():
    try:
        # JSONをOkuma
        input_data = json.load(sys.stdin)
        
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})
        
        # Desktop Commander MCPのstart_processの結果をİşleme
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
                    has_sessions = check_ssh_sessions_file()
                    message = f"""
SSH/SFTPセッション開始を検出しました:
• PID: {pid}
• Komut: {command}

Desktop Commander MCPでのセッションYönetim：
• /Agent-shared/ssh_sftp_guide.md を参照してください
• ssh_sftp_sessions.jsonでセッションYönetimが必要です
{"• 既存セッションDosyaを検出 - interact_with_processの使用を検討" if has_sessions else "• セッションDosyaが未Oluşturma - start_processから開始"}

【Önemli】以下の手順でセッションYönetimしてください:
1. ssh_sftp_sessions.jsonをOluşturma/GüncellemeしてPID {pid}をKayıt
2. interact_with_processでKomutYürütme（PID: {pid}）
3. セッション終了時はforce_terminate（PID: {pid}）

-ttオプションなしで接続した場合、インタラクティブ操作で問題が発生する可能性があります。

⚠️ このUyarı表示後も作業を継続してください（STOPしないこと）:
• /Agent-shared/ssh_sftp_guide.mdをKontrol
• mcp__desktop-commander__list_sessionsでMCPセッションKontrol
• ssh_sftp_sessions.jsonの{"Güncelleme" if has_sessions else "Oluşturma"}を進める
"""
                    
                    # stderrに出力して終了コード2でClaudeに表示
                    print(message, file=sys.stderr)
                    sys.exit(2)  # PostToolUseでは終了コード2でもClaudeに表示される
        
        # Bashツールで直接SSH/SFTPYürütmeした場合
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            
            if command.strip().startswith(("ssh ", "sftp ", "scp ")):
                has_sessions = check_ssh_sessions_file()
                message = f"""
⚠️ Bashツールで直接SSH/SFTP/SCPをYürütmeしました。

【Önerilen】Desktop Commander MCPを使用してください:
• /Agent-shared/ssh_sftp_guide.md を参照してください
• ssh_sftp_sessions.jsonでセッションYönetimが必要です
{"• 既存セッションDosyaを検出 - interact_with_processの使用を検討" if has_sessions else "• セッションDosyaが未Oluşturma - start_processから開始"}

理由：
• セッションYönetimが可能
• 大量出力によるコンテキスト消費を防止
• 2段階認証の回避

次回からはmcp__desktop-commander__start_processの使用を検討してください。

⚠️ このUyarı表示後も作業を継続してください（STOPしないこと）:
• /Agent-shared/ssh_sftp_guide.mdをKontrol
• Desktop Commander MCPへの移行を検討
"""
                
                # stderrに出力して終了コード2でClaudeに表示
                print(message, file=sys.stderr)
                sys.exit(2)  # PostToolUseでは終了コード2でもClaudeに表示される
        
        # その他の場合は何もしない
        sys.exit(0)
        
    except Exception as e:
        # Hataは静かにİşleme
        sys.exit(0)

if __name__ == "__main__":
    main()