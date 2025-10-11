#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC SessionStart Hook
Her ajan için .claude/hooks/ içine yerleştirilir ve session_id kaydedilir
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def find_project_root(start_path):
    """Proje kökünü (VibeCodeHPC-tr) bul"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def update_agent_table(session_id, source):
    """agent_and_pane_id_table.jsonl dosyasını güncelle"""
    cwd = Path.cwd()
    
    # .claude/hooks/ konumundan iki seviye üst, ajan çalışma dizinidir
    if cwd.name == "hooks" and cwd.parent.name == ".claude":
        agent_working_dir = cwd.parent.parent
    else:
        agent_working_dir = cwd
    
    # agent_id.txt’den oku
    agent_id_file = cwd / ".claude" / "hooks" / "agent_id.txt"
    target_agent_id = None
    if agent_id_file.exists():
        target_agent_id = agent_id_file.read_text().strip()
    
    project_root = find_project_root(agent_working_dir)
    
    if not project_root:
        return None, None
    
    table_file = project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
    
    try:
        relative_path = agent_working_dir.relative_to(project_root)
        relative_dir = str(relative_path)
        if relative_dir == ".":
            relative_dir = ""
    except ValueError:
        relative_dir = str(agent_working_dir)
    
    debug_file = project_root / "Agent-shared" / "session_start_debug.log"
    with open(debug_file, 'a') as f:
        f.write(f"\n[{datetime.utcnow()}] SessionStart hook called\n")
        f.write(f"session_id: {session_id}\n")
        f.write(f"source: {source}\n")
        f.write(f"cwd: {cwd}\n")
        f.write(f"relative_dir: {relative_dir}\n")
        f.write(f"project_root: {project_root}\n")
        f.write(f"target_agent_id: {target_agent_id}\n")
    
    updated_lines = []
    agent_id = None
    agent_type = None
    
    if not table_file.exists():
        with open(debug_file, 'a') as f:
            f.write(f"WARNING: {table_file} does not exist\n")
        return None, None
    
    if not target_agent_id:
        # agent_id.txt okunamazsa hata ayıklama bilgisi
        with open(debug_file, 'a') as f:
            f.write(f"WARNING: agent_id.txt not found or empty at {agent_id_file}\n")
        return None, None
    
    if table_file.exists():
        with open(table_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                entry = json.loads(line)
                
                # agent_id ile eşleştir
                match_found = False
                
                # target_agent_id alınabildiyse agent_id ile karşılaştır
                if target_agent_id and entry.get('agent_id') == target_agent_id:
                    match_found = True
                    with open(debug_file, 'a') as f:
                        f.write(f"MATCH by agent_id: entry='{entry['agent_id']}' target='{target_agent_id}'\n")
                
                if match_found:
                    with open(debug_file, 'a') as f:
                        f.write(f"Updating agent_id={entry['agent_id']} with session_id={session_id}\n")
                    
                    entry['claude_session_id'] = session_id
                    entry['status'] = 'running'
                    entry['last_updated'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                    entry['cwd'] = str(cwd)
                    agent_id = entry['agent_id']
                    
                    agent_type = 'polling'
                    
                    if (agent_id == 'PM' or agent_id == 'SOLO') and source == 'startup':
                        start_time_file = project_root / "Agent-shared" / "project_start_time.txt"
                        if not start_time_file.exists() or start_time_file.stat().st_size == 0:
                            start_time_file.write_text(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ\n'))
                        
                        periodic_script = project_root / "telemetry" / "periodic_monitor.sh"
                        if periodic_script.exists():
                            import subprocess
                            try:
                                subprocess.Popen(
                                    ['bash', str(periodic_script)],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    start_new_session=False  # tmuxセッションに紐づける
                                )
                                with open(debug_file, 'a') as f:
                                    f.write(f"Periyodik izleyici başlatıldı: {periodic_script}\n")
                            except Exception as e:
                                with open(debug_file, 'a') as f:
                                    f.write(f"Periyodik izleyici başlatılamadı: {e}\n")
                
                updated_lines.append(json.dumps(entry, ensure_ascii=False))
        
        try:
            with open(table_file, 'w') as f:
                f.write('\n'.join(updated_lines) + '\n')
            
            with open(debug_file, 'a') as f:
                f.write(f"Successfully wrote {len(updated_lines)} lines to {table_file}\n")
        except Exception as e:
            with open(debug_file, 'a') as f:
                f.write(f"ERROR writing to {table_file}: {str(e)}\n")
    
    return agent_id, agent_type


def get_required_files(agent_id):
    """Ajana göre gerekli dosya listesini döndür"""
    # 共通ファイル
    common_files = [
        "CLAUDE.md",
        "Agent-shared/directory_pane_map.txt"
    ]
    
    # 役割を抽出（例: PG1.1.1 -> PG）
    role = agent_id.split('.')[0].rstrip('0123456789') if agent_id else ''
    
    role_files = {
        "PM": [
            "instructions/PM.md",
            "_remote_info/",
            "Agent-shared/strategies/auto_tuning/typical_hpc_code.md",
            "Agent-shared/strategies/auto_tuning/evolutional_flat_dir.md",
            "requirement_definition.md(varsa)"
        ],
        "SE": [
            "instructions/SE.md",
            "Agent-shared/change_log/changelog_analysis_template.py"
        ],
        "PG": [
            "instructions/PG.md",
            "Geçerli dizindeki ChangeLog.md",
            "Agent-shared/change_log/ChangeLog_format.md",
            "Agent-shared/change_log/ChangeLog_format_PM_override.md(varsa)"
        ],
        "CD": [
            "instructions/CD.md"
        ],
        "SOLO": [
            "instructions/SOLO.md",
            "requirement_definition.md(varsa)"
        ]
    }
    
    files = common_files.copy()
    if role in role_files:
        files.extend(role_files[role])
    
    return files


def generate_context(source, agent_id, agent_type):
    """Oturum başlangıcında bağlam oluştur"""
    context_parts = []
    
    if source in ['startup', 'clear']:
        context_parts.append("## ⚠️ Oturum başlangıcı")
        context_parts.append("")
        context_parts.append("VibeCodeHPC ajanı olarak başlatıldınız.")
        context_parts.append("Aşağıdaki adımlarla gerekli dosyaları yükleyin:")
        context_parts.append("")
        
        files = get_required_files(agent_id)
        context_parts.append("### 1. Gerekli dosyaları yeniden yükle")
        for file in files:
            context_parts.append(f"- {file}")
        
        context_parts.append("")
        context_parts.append("### 2. Dizin yapısını doğrula")
        context_parts.append("```bash")
        context_parts.append("pwd  # Mevcut konumu doğrula")
        context_parts.append("ls -R ../../../../Agent-shared/")
        context_parts.append("ls -R ../../../../instructions/")
        context_parts.append("```")
        
        if agent_type == 'polling':
            context_parts.append("")
            context_parts.append("### 3. Polling tipi ajan olarak devam")
            context_parts.append("Siz bir polling tipi ajansınız.")
            context_parts.append("Bekleme durumuna geçmeden düzenli aralıklarla görevleri kontrol edin.")
        
        if agent_id == 'CD' or agent_id == 'SOLO':
            context_parts.append("")
            context_parts.append("### 📌 Git yönetimi için öneriler")
            context_parts.append("Gereksinimler belgesinde açıkça yasaklanmadıkça,")
            context_parts.append("kullanıcının ilerlemeyi görebilmesi için **sık sık git push** yapın.")
            context_parts.append("Küçük değişikliklerde bile düzenli olarak commit ve push önerilir.")
    
    return "\n".join(context_parts) if context_parts else None


def main():
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id')
        source = input_data.get('source', 'startup')  # startup(新規起動), resume(--continue), clear(/clear)
        
        agent_id, agent_type = update_agent_table(session_id, source)
        
        context = generate_context(source, agent_id, agent_type)
        
        if context:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context
                }
            }
            print(json.dumps(output, ensure_ascii=False))
        
        sys.exit(0)
        
    except Exception as e:
        try:
            from pathlib import Path
            cwd = Path.cwd()
            project_root = find_project_root(cwd)
            if project_root:
                debug_file = project_root / "Agent-shared" / "session_start_debug.log"
                with open(debug_file, 'a') as f:
                    f.write(f"\n[{datetime.utcnow()}] EXCEPTION in main(): {str(e)}\n")
                    import traceback
                    f.write(traceback.format_exc())
        except:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
