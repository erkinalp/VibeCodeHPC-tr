#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# uvがある場合は以下で実行されます:
# #!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
VibeCodeHPC SessionStart Hook
各エージェントの.claude/hooks/に配置してsession_idを記録
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def find_project_root(start_path):
    """プロジェクトルート（VibeCodeHPC-jp）を探す"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def update_agent_table(session_id, source):
    """agent_and_pane_id_table.jsonlを更新"""
    cwd = Path.cwd()
    
    # hooksディレクトリから実際の作業ディレクトリを取得
    # .claude/hooks/ から2階層上がエージェントの作業ディレクトリ
    if cwd.name == "hooks" and cwd.parent.name == ".claude":
        agent_working_dir = cwd.parent.parent
    else:
        # 通常はここに来ないはずだが、念のため
        agent_working_dir = cwd
    
    # agent_id.txtから読み取り
    agent_id_file = cwd / ".claude" / "hooks" / "agent_id.txt"
    target_agent_id = None
    if agent_id_file.exists():
        target_agent_id = agent_id_file.read_text().strip()
    
    project_root = find_project_root(agent_working_dir)
    
    if not project_root:
        return None, None
    
    table_file = project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
    
    # プロジェクトルートからの相対パス（OS固有の形式を保持）
    try:
        relative_path = agent_working_dir.relative_to(project_root)
        relative_dir = str(relative_path)
        if relative_dir == ".":
            relative_dir = ""
    except ValueError:
        relative_dir = str(agent_working_dir)
    
    # デバッグ: 環境変数の状態を記録
    debug_file = project_root / "Agent-shared" / "session_start_debug.log"
    with open(debug_file, 'a') as f:
        f.write(f"\n[{datetime.utcnow()}] SessionStart hook called\n")
        f.write(f"session_id: {session_id}\n")
        f.write(f"source: {source}\n")
        f.write(f"cwd: {cwd}\n")
        f.write(f"relative_dir: {relative_dir}\n")
        f.write(f"project_root: {project_root}\n")
        f.write(f"target_agent_id: {target_agent_id}\n")
    
    # ファイルを読み込んで更新
    updated_lines = []
    agent_id = None
    agent_type = None
    
    if not table_file.exists():
        # ファイルが存在しない場合のデバッグ情報
        with open(debug_file, 'a') as f:
            f.write(f"WARNING: {table_file} does not exist\n")
        return None, None
    
    if not target_agent_id:
        # agent_id.txtが読み取れない場合のデバッグ情報
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
                
                # agent_idでマッチング
                match_found = False
                
                # target_agent_idが取得できている場合はagent_idで比較
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
                    
                    # エージェントタイプを判定
                    # v0.5: 全エージェントがポーリング型
                    # v0.6以降: テスト検証エージェントの追加を検討
                    agent_type = 'polling'
                    
                    # PMが初回起動時にプロジェクト開始時刻を記録と定期実行開始
                    if agent_id == 'PM' and source == 'startup':
                        start_time_file = project_root / "Agent-shared" / "project_start_time.txt"
                        if not start_time_file.exists() or start_time_file.stat().st_size == 0:
                            start_time_file.write_text(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ\n'))
                        
                        # 定期実行をバックグラウンドで開始
                        periodic_script = project_root / "telemetry" / "periodic_monitor.sh"
                        if periodic_script.exists():
                            import subprocess
                            try:
                                # nohupでバックグラウンド実行、tmux解除でも継続しない
                                subprocess.Popen(
                                    ['bash', str(periodic_script)],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    start_new_session=False  # tmuxセッションに紐づける
                                )
                                with open(debug_file, 'a') as f:
                                    f.write(f"Started periodic monitor from {periodic_script}\n")
                            except Exception as e:
                                with open(debug_file, 'a') as f:
                                    f.write(f"Failed to start periodic monitor: {e}\n")
                
                updated_lines.append(json.dumps(entry, ensure_ascii=False))
        
        # ファイルを書き戻す
        try:
            with open(table_file, 'w') as f:
                f.write('\n'.join(updated_lines) + '\n')
            
            # デバッグ: 書き込み成功を記録
            with open(debug_file, 'a') as f:
                f.write(f"Successfully wrote {len(updated_lines)} lines to {table_file}\n")
        except Exception as e:
            # デバッグ: 書き込みエラーを記録
            with open(debug_file, 'a') as f:
                f.write(f"ERROR writing to {table_file}: {str(e)}\n")
    
    return agent_id, agent_type


def get_required_files(agent_id):
    """エージェントに応じた必須ファイルリストを返す"""
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
            "Agent-shared/typical_hpc_code.md",
            "Agent-shared/evolutional_flat_dir.md",
            "requirement_definition.md（存在する場合）"
        ],
        "SE": [
            "instructions/SE.md",
            "Agent-shared/changelog_analysis_template.py"
        ],
        "PG": [
            "instructions/PG.md",
            "現在のディレクトリのChangeLog.md",
            "Agent-shared/ChangeLog_format.md",
            "Agent-shared/ChangeLog_format_PM_override.md（存在する場合）"
        ],
        "CD": [
            "instructions/CD.md"
        ]
    }
    
    files = common_files.copy()
    if role in role_files:
        files.extend(role_files[role])
    
    return files


def generate_context(source, agent_id, agent_type):
    """セッション開始時のコンテキストを生成"""
    context_parts = []
    
    if source in ['startup', 'clear']:
        context_parts.append("## ⚠️ セッション開始")
        context_parts.append("")
        context_parts.append("VibeCodeHPCエージェントとして起動しました。")
        context_parts.append("以下の手順で必須ファイルを読み込んでください：")
        context_parts.append("")
        
        # 必須ファイルリスト
        files = get_required_files(agent_id)
        context_parts.append("### 1. 必須ファイルの再読み込み")
        for file in files:
            context_parts.append(f"- {file}")
        
        context_parts.append("")
        context_parts.append("### 2. ディレクトリ構造の確認")
        context_parts.append("```bash")
        context_parts.append("pwd  # 現在位置確認")
        context_parts.append("ls -R ../../../../Agent-shared/")
        context_parts.append("ls -R ../../../../instructions/")
        context_parts.append("```")
        
        if agent_type == 'polling':
            context_parts.append("")
            context_parts.append("### 3. ポーリング型エージェントとしての再開")
            context_parts.append("あなたはポーリング型エージェントです。")
            context_parts.append("待機状態に入らず、定期的にタスクを確認してください。")
    
    return "\n".join(context_parts) if context_parts else None


def main():
    try:
        # 入力を読み込み
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id')
        source = input_data.get('source', 'startup')  # startup(新規起動), resume(--continue), clear(/clear)
        
        # テーブルを更新してエージェント情報を取得
        agent_id, agent_type = update_agent_table(session_id, source)
        
        # コンテキストを生成
        context = generate_context(source, agent_id, agent_type)
        
        if context:
            # コンテキストを追加
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context
                }
            }
            print(json.dumps(output, ensure_ascii=False))
        
        sys.exit(0)
        
    except Exception as e:
        # エラーをデバッグログに記録
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