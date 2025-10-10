#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC PreToolUse Hook for SSH/SFTP Validation
Desktop Commander MCPのSSH接続を支援・Bashツールの直接SSH使用をUyarı
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re

def find_project_root(start_path):
    """Projeルート（VibeCodeHPC-jp）を探す"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None

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

def get_agent_id():
    """現在のAjanIDをAlma"""
    agent_id_file = Path.cwd() / ".claude" / "hooks" / "agent_id.txt"
    if agent_id_file.exists():
        return agent_id_file.read_text().strip()
    return "unknown"

def main():
    try:
        # JSONをOkuma
        input_data = json.load(sys.stdin)
        
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        
        # Bashツールで直接SSH/SFTPを使おうとしている場合
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            
            # SSH/SFTPKomutの検出
            if re.match(r'^\s*(ssh|sftp|scp)\s+', command):
                # ssh_sftp_sessions.jsonがあるかチェック
                has_sessions = check_ssh_sessions_file()
                
                warning_message = f"""⚠️ 直接Bashでのssh/sftpYürütmeを検出しました。

Desktop Commander MCPの使用を強くÖnerilenします：
• /Agent-shared/ssh_sftp_guide.md を参照してください
• ssh_sftp_sessions.jsonでセッションYönetimが必要です
{"• 既存セッションDosyaを検出 - interact_with_processの使用を検討" if has_sessions else "• セッションDosyaが未Oluşturma - start_processから開始"}

理由：
1. 2段階認証の回避（一度接続すれば再認証不要）
2. 大量の標準出力によるコンテキスト浪費の防止
3. セッションの永続化と再利用

このままYürütmeする場合は、大量の出力にDikkatしてください。"""
                
                # Uyarıのみ表示（ブロックはしない）
                output = {
                    "systemMessage": warning_message,
                    "suppressOutput": False,
                    "continue": True
                }
                print(json.dumps(output))
                sys.exit(0)
        
        # Desktop Commander MCPのstart_processでSSH使用時のアドバイス
        elif tool_name == "mcp__desktop-commander__start_process":
            command = tool_input.get("command", "")
            
            if command.startswith("ssh "):
                # -ttオプションのÖnerilen（強制ではない）
                if " -tt " not in command and not command.startswith("ssh -tt"):
                    advice = "SSH接続に-ttオプションの使用を推奨（PTY確保でインタラクティブ操作が安定）"
                    session_reminder = "返されたPIDを必ずssh_sftp_sessions.jsonに記録してください"
                    
                    # 終了コード2でブロック＆Claudeに表示（でも続行したいので使わない方がいい）
                    print(f"💡 {advice}\n• {session_reminder}", file=sys.stderr)
                    sys.exit(0)  # 終了コード0で、stdoutはトランスクリプトモードでのみ表示
                
                # セッションYönetimのリマインダーのみ
                print("• 返されたPIDを必ずssh_sftp_sessions.jsonに記録してください", file=sys.stderr)
                sys.exit(1)  # 非ブロッキングエラーでClaudeにもstderrが見える
            
            elif command.startswith("sftp "):
                # SFTPの場合はセッションYönetimのリマインダーのみ
                print("• 返されたPIDを必ずssh_sftp_sessions.jsonに記録してください", file=sys.stderr)
                sys.exit(1)  # 非ブロッキングエラーでClaudeにもstderrが見える
        
        # その他の場合は何もしない
        sys.exit(0)
        
    except Exception as e:
        # Hataは静かにİşleme
        sys.exit(0)

if __name__ == "__main__":
    main()