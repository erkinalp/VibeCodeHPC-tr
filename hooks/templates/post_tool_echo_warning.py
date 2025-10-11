#!/usr/bin/env python3
"""
echo çıktısı tespit kancası - agent_send.sh kullanımını teşvik eder
PostToolUse sırasında çalışır ve ajanlar arası iletişimde hatalı kullanımı önler
Sadece Bash aracı için (Desktop Commander hariç)
"""

import sys
import json
import re

def main():
    # PostToolUse kancasının girdisini oku
    try:
        input_data = json.loads(sys.stdin.read())
    except:
        return 0
    
    tool_name = input_data.get('name', '')
    if tool_name != 'Bash':
        return 0
    
    params = input_data.get('params', {})
    command = params.get('command', '')
    
    agent_pattern = r'\b(PM|SE\d*|PG\d+\.\d+|CD)\b'
    
    # echo/printf komutunda ajan adı varsa
    if re.match(r'^\s*(echo|printf)\s+', command):
        if '>' not in command:
            if re.search(agent_pattern, command):
                print("⚠️ Ajanlar arası iletişim için agent_send.sh kullanın", file=sys.stderr)
                print("Örnek: ./communication/agent_send.sh SE1 \"[Rapor] Görev tamamlandı\"", file=sys.stderr)
                print("", file=sys.stderr)
                print("echo yalnızca ekranda gösterir, diğer ajanlara ulaşmaz.", file=sys.stderr)
                return 2  # Claudeに警告を表示
            
            message_keywords = ['報告', '依頼', '質問', '完了', '連絡', '通知']
            for keyword in message_keywords:
                if keyword in command:
                    print("⚠️ Mesaj göndermek için agent_send.sh kullanın", file=sys.stderr)
                    print("Örnek: ./communication/agent_send.sh PM \"[{}] İçerik\"".format(keyword), file=sys.stderr)
                    return 2
    
    # tmux send-keys ile Claude'a yönelik doğrudan işlemi tespit et
    if 'tmux send-keys' in command:
        if 'claude' in command.lower() or re.search(agent_pattern, command):
            print("⚠️ tmux send-keys'in doğrudan kullanımından kaçının", file=sys.stderr)
            print("agent_send.sh kullanarak mesajları güvenilir şekilde iletebilirsiniz.", file=sys.stderr)
            print("", file=sys.stderr)
            print("tmux send-keys yalnızca Claude başlamadan önce komut göndermek veya PM'in acil durdurması için kullanılır.", file=sys.stderr)
            print("Ajanlar arası iletişim için mutlaka agent_send.sh kullanın.", file=sys.stderr)
            return 2  # Claudeに警告を表示
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
