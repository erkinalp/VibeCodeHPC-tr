#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC PreToolUse Hook for SSH/SFTP Validation
Desktop Commander MCP üzerinden SSH bağlantısını destekler; Bash aracında doğrudan SSH kullanımını uyarır
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re

def find_project_root(start_path):
    """Proje kökünü (VibeCodeHPC-tr) bul"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None

def check_ssh_sessions_file():
    """ssh_sftp_sessions.json dosyasının varlığını doğrula"""
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
    """Geçerli ajan kimliğini al"""
    agent_id_file = Path.cwd() / ".claude" / "hooks" / "agent_id.txt"
    if agent_id_file.exists():
        return agent_id_file.read_text().strip()
    return "unknown"

def main():
    try:
        input_data = json.load(sys.stdin)
        
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            
            # SSH/SFTP komutunu tespit et
            if re.match(r'^\s*(ssh|sftp|scp)\s+', command):
                # ssh_sftp_sessions.json var mı kontrol et
                has_sessions = check_ssh_sessions_file()
                
                warning_message = f"""⚠️ Bash aracıyla doğrudan ssh/sftp çalıştırılması tespit edildi."""

Desktop Commander MCP kullanımını şiddetle öneririz:
• /Agent-shared/ssh_sftp_guide.md dosyasına bakın
• ssh_sftp_sessions.json ile oturum yönetimi gereklidir
{"• Var olan oturum dosyası bulundu - interact_with_process kullanımını değerlendirin" if has_sessions else "• Oturum dosyası oluşturulmamış - start_process ile başlayın"}

Gerekçe:
1. İki aşamalı doğrulama sorunlarının önlenmesi (bir kez bağlanınca yeniden doğrulama gerekmeyebilir)
2. Büyük standart çıkışların bağlam tüketimini önler
3. Oturumun kalıcı hale getirilmesi ve yeniden kullanım

Bu şekilde çalıştırmaya devam edecekseniz, büyük çıktılara dikkat edin."""
                
                output = {
                    "systemMessage": warning_message,
                    "suppressOutput": False,
                    "continue": True
                }
                print(json.dumps(output))
                sys.exit(0)
        
        # Desktop Commander MCP start_process ile SSH kullanımında öneriler
        elif tool_name == "mcp__desktop-commander__start_process":
            command = tool_input.get("command", "")
            
            if command.startswith("ssh "):
                if " -tt " not in command and not command.startswith("ssh -tt"):
                    advice = "SSH bağlantısında -tt seçeneğinin kullanılmasını öneririz (PTY ayırma ile etkileşimli işlemler daha kararlı olur)"
                    session_reminder = "Dönen PID'yi mutlaka ssh_sftp_sessions.json dosyasına kaydedin"
                    
                    # 終了コード2でブロック＆Claudeに表示（でも続行したいので使わない方がいい）
                    print(f"💡 {advice}\n• {session_reminder}", file=sys.stderr)
                    sys.exit(0)  # 終了コード0で、stdoutはトランスクリプトモードでのみ表示
                
                # セッション管理のリマインダーのみ
                print("• Dönen PID'yi mutlaka ssh_sftp_sessions.json dosyasına kaydedin", file=sys.stderr)
                sys.exit(1)  # 非ブロッキングエラーでClaudeにもstderrが見える
            
            elif command.startswith("sftp "):
                # SFTPの場合はセッション管理のリマインダーのみ
                print("• Dönen PID'yi mutlaka ssh_sftp_sessions.json dosyasına kaydedin", file=sys.stderr)
                sys.exit(1)  # 非ブロッキングエラーでClaudeにもstderrが見える
        
        # その他の場合は何もしない
        sys.exit(0)
        
    except Exception as e:
        # エラーは静かに処理
        sys.exit(0)

if __name__ == "__main__":
    main()
