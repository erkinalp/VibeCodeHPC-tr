#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sürüm dosyası oluşturulduğunda ChangeLog.md tutarlılık kontrolü
_v*.* desenindeki dosya oluşturmayı algılar ve alt ajanla kontrol eder
"""

import json
import sys
import re
import subprocess
from pathlib import Path


def find_project_root(start_path):
    """Proje kökünü (VibeCodeHPC-jp) bul"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def check_changelog_with_subagent(version, cwd):
    """Alt ajan kullanarak ChangeLog.md'yi kontrol et"""
    changelog_path = Path(cwd) / "ChangeLog.md"
    
    if not changelog_path.exists():
        return False, "ChangeLog.md not found"
    
    query = f"""
Aşağıdakileri doğrulayın ve YES/NO ile yanıtlayın:
1. v{version} girdisi mevcut mu
2. job bölümünde resource_group belirtilmiş mi
3. start_time veya end_time belirtilmiş mi

Mevcut değilse "NO: gerekçe" biçiminde yanıtlayın.
"""
    
    try:
        result = subprocess.run(
            ["claude", "-p", query],
            input=changelog_path.read_text(),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        response = result.stdout.strip()
        if response.startswith("YES"):
            return True, None
        else:
            return False, response
            
    except Exception as e:
        return False, str(e)


def main():
    try:
        input_data = json.load(sys.stdin)
        
        if input_data.get('hook_event_name') != 'PostToolUse':
            sys.exit(0)
        
        if input_data.get('tool_name') not in ['Write', 'Edit', 'MultiEdit']:
            sys.exit(0)
        
        file_path = input_data.get('tool_input', {}).get('file_path', '')
        
        version_match = re.search(r'_v(\d+\.\d+\.\d+)\.\w+$', file_path)
        if not version_match:
            sys.exit(0)
        
        version = version_match.group(1)
        cwd = Path(input_data.get('cwd', '.'))
        
        project_root = find_project_root(cwd)
        if not project_root:
            sys.exit(0)
        
        debug_file = project_root / "Agent-shared" / "ci_check_debug.log"
        with open(debug_file, 'a') as f:
            from datetime import datetime
            f.write(f"\n[{datetime.utcnow()}] Version check for {version}\n")
            f.write(f"File: {file_path}\n")
            f.write(f"CWD: {cwd}\n")
        
        # ChangeLog.md kontrolü
        is_valid, error_msg = check_changelog_with_subagent(version, cwd)
        
        if not is_valid:
            print(f"""
⚠️ ChangeLog.md içinde v{version} için gerekli bilgiler eksik

{error_msg}

Lütfen aşağıdaki biçimde ekleyin:

### v{version}
**oluşturma_zamanı**: `YYYY-MM-DDTHH:MM:SSZ`
**değişiklikler**: "değişiklik içeriği"
**sonuç**: performans değeri `XXX GFLOPS`

<details>

- [ ] **job**
    - id: `job_id`
    - resource_group: `cx-small vb.`  # zorunlu
    - start_time: `başlangıç_zamanı`  # zorunlu
    - end_time: `bitiş_zamanı`  # zorunlu (çalışma sonrası)
    - runtime_sec: `çalışma_süresi_saniye`  # zorunlu (çalışma sonrası)
    - status: `pending/running/completed/cancelled`

</details>
""", file=sys.stderr)
            sys.exit(2)  # Bloklayıcı hata
        
        print(f"✅ v{version} entry validated in ChangeLog.md")
        sys.exit(0)
        
    except Exception as e:
        try:
            debug_file = Path.cwd() / ".." / ".." / "Agent-shared" / "ci_check_debug.log"
            with open(debug_file, 'a') as f:
                from datetime import datetime
                import traceback
                f.write(f"\n[{datetime.utcnow()}] ERROR: {str(e)}\n")
                f.write(traceback.format_exc())
        except:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
