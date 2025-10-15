#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC PostToolUse Hook for SSH/SFTP Handler
Araç çalıştıktan sonra PID bilgisi ve oturum yönetimi önerileri sağlar
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def check_ssh_sessions_file():
    """ssh_sftp_sessions.json varlığını kontrol et"""
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
        input_data = json.load(sys.stdin)
        
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})
        
        # Desktop Commander MCP start_process sonucunu işle
        if tool_name == "mcp__desktop-commander__start_process":
            command = tool_input.get("command", "")
            
            if command.startswith(("ssh ", "sftp ")):
                response_text = str(tool_response)
                pid = None
                
                # "Process started with PID XXXXX" desenini ara
                import re
                pid_match = re.search(r'PID (\d+)', response_text)
                if pid_match:
                    pid = pid_match.group(1)
                
                if pid:
                    has_sessions = check_ssh_sessions_file()
                    message = f"""
SSH/SFTP oturumu başlangıcı tespit edildi:
• PID: {pid}
• Komut: {command}

Desktop Commander MCP ile oturum yönetimi:
• /Agent-shared/ssh_sftp_guide.md dosyasına bakın
• ssh_sftp_sessions.json ile oturum yönetimi gereklidir
{"• Var olan oturum dosyası bulundu - interact_with_process kullanımını değerlendirin" if has_sessions else "• Oturum dosyası oluşturulmamış - start_process ile başlayın"}

[Önemli]Aşağıdaki adımlarla oturum yönetimi yapın:
1. ssh_sftp_sessions.json dosyasını oluştur/güncelle ve PID {pid} kaydet
2. interact_with_process ile komut çalıştır (PID: {pid})
3. Oturum bittiğinde force_terminate (PID: {pid})

-tt seçeneği olmadan bağlandıysanız interaktif işlemlerde sorun yaşayabilirsiniz.

⚠️ Bu uyarıdan sonra da çalışmaya devam edin (STOP etmeyin):
• /Agent-shared/ssh_sftp_guide.md'yi kontrol edin
• mcp__desktop-commander__list_sessions ile MCP oturumlarını kontrol edin
• ssh_sftp_sessions.json için {"güncelleme" if has_sessions else "oluşturma"} işlemini ilerletin
"""
                    
                    print(message, file=sys.stderr)
                    sys.exit(2)  # PostToolUse'de çıkış kodu 2 olsa da Claude'da görüntülenir
        
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            
            if command.strip().startswith(("ssh ", "sftp ", "scp ")):
                has_sessions = check_ssh_sessions_file()
                message = f"""
⚠️ Bash aracıyla doğrudan SSH/SFTP/SCP çalıştırdınız.

[Öneri]Desktop Commander MCP kullanın:
• /Agent-shared/ssh_sftp_guide.md dosyasına bakın
• ssh_sftp_sessions.json ile oturum yönetimi gereklidir
{"• Var olan oturum dosyası bulundu - interact_with_process kullanımını değerlendirin" if has_sessions else "• Oturum dosyası oluşturulmamış - start_process ile başlayın"}

Gerekçe:
• Oturum yönetimi mümkündür
• Büyük çıktılarda bağlam tüketimini önler
• İki aşamalı doğrulama sorunlarının önlenmesi

Bir sonraki sefer mcp__desktop-commander__start_process kullanımını değerlendirin.

⚠️ Bu uyarıdan sonra da çalışmaya devam edin (STOP etmeyin):
• /Agent-shared/ssh_sftp_guide.md'yi kontrol edin
• Desktop Commander MCP'ye geçişi değerlendirin
"""
                
                print(message, file=sys.stderr)
                sys.exit(2)  # PostToolUse'de çıkış kodu 2 olsa da Claude'da görüntülenir
        
        sys.exit(0)
        
    except Exception as e:
        sys.exit(0)

if __name__ == "__main__":
    main()
