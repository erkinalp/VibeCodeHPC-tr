#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
OpenCodeAT Stop Hook (ポーリング型エージェント用)
PM, SE, CI, CDの待機状態を防ぐ
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def find_project_root(start_path):
    """プロジェクトルート（OpenCodeAT-jp）を探す"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def get_agent_info_from_session(session_id):
    """session_idから自分のエージェント情報を取得"""
    project_root = find_project_root(Path.cwd())
    
    if not project_root:
        return None
    
    table_file = project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
    
    if table_file.exists():
        with open(table_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get('claude_session_id') == session_id:
                    return entry
    
    return None


def get_required_files(agent_id):
    """エージェントIDから必須ファイルリストを生成"""
    # 共通の必須ファイル
    common_files = [
        "CLAUDE.md",
        "Agent-shared/directory_map.txt"
    ]
    
    # 役割を抽出
    role = agent_id.split('.')[0].rstrip('0123456789') if agent_id else ''
    
    role_files = {
        "PM": ["instructions/PM.md", "_remote_info/", "Agent-shared/typical_hpc_code.md", "Agent-shared/evolutional_flat_dir.md"],
        "SE": ["instructions/SE.md", "Agent-shared/changelog_analysis_template.py"],
        "CI": ["instructions/CI.md", "_remote_info/*/command.md", "Agent-shared/ssh_guide.md"],
        "CD": ["instructions/CD.md"]
    }
    
    files = common_files.copy()
    if role in role_files:
        files.extend(role_files[role])
    
    return files


def generate_block_reason(agent_info, stop_hook_active):
    """ポーリング型エージェント用のブロック理由を生成"""
    
    # stop_hook_activeがtrueの場合は、繰り返しを防ぐ
    if stop_hook_active:
        return None
    
    agent_id = agent_info.get('agent_id', 'unknown')
    required_files = get_required_files(agent_id)
    
    reason = f"""あなたはポーリング型のエージェント（{agent_id}）です。待機状態に入ることは許可されていません。

以下のファイルを再度読み込んで、プロジェクトの最新状態を確認してください：
{chr(10).join(f'- {file}' for file in required_files)}

さらに、以下のディレクトリの内容を確認してください：
- ls -R Agent-shared/
- ls -R instructions/
- ls -R communication/

確認後、以下の並行タスクを進めてください：

"""
    
    # 役割別の並行タスク
    if "PM" in agent_id:
        reason += """【PMの並行タスク】
1. 全エージェントの進捗確認（SE、CI、PG、CDの巡回）
2. directory_map.txtの更新確認
3. 予算管理（pjstatでポイント確認）
4. 停滞エージェントへの介入
5. リソース再配分の検討

定期巡回は2-5分間隔で実施してください。
"""
    
    elif agent_id.startswith("SE"):
        reason += """【SEの並行タスク】
1. 各PGのChangeLog.md更新状況の監視
2. telemetry/context_usage_monitor.pyでコンテキスト使用状況確認
3. SOTA更新履歴のグラフ生成（Agent-shared/log_analyzer.py）
4. CI待ち状態のPGの検出と対応
5. visible_path_PG*.txtの更新

停滞検知は3-10分間隔（計算時間に応じて）で実施してください。
"""
    
    elif agent_id.startswith("CI"):
        reason += """【CIの並行タスク】
1. 各PGのChangeLog.mdを確認し、未実行のコードをチェック
2. SSH/SFTPセッションの状態確認（Desktop Commander利用）
3. ジョブキューの状態確認（squeue等）
4. コンパイル警告の解析とPGへのフィードバック
5. /resultsディレクトリの整理

非同期でPGの要求に対応してください。
"""
    
    elif agent_id.startswith("CD"):
        reason += """【CDの並行タスク】
1. 各PGのSOTA達成コードの確認
2. GitHub/ディレクトリへのコピーと匿名化処理
3. .gitignoreの更新確認
4. git statusでの変更確認
5. コミットメッセージの準備

非同期でGitHub同期を進めてください。
"""
    
    reason += """
それでも待機する必要がある場合は、sleep 10 等を使用してください。
"""
    
    return reason


def main():
    try:
        # JSONを読み込み
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id')
        stop_hook_active = input_data.get('stop_hook_active', False)
        
        # 自分のエージェント情報を取得
        agent_info = get_agent_info_from_session(session_id)
        
        if agent_info:
            # ポーリング型エージェントの場合は停止をブロック
            reason = generate_block_reason(agent_info, stop_hook_active)
            
            if reason:  # stop_hook_activeでない場合のみ
                output = {
                    "decision": "block",
                    "reason": reason
                }
                print(json.dumps(output, ensure_ascii=False))
                sys.exit(0)
        
        # 通常終了
        sys.exit(0)
        
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()