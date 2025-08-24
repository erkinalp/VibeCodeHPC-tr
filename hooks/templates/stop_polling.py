#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook (ポーリング型エージェント用)
PM, SE, PG, CDの待機状態を防ぐ
"""

import json
import os
import sys
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


def get_agent_info_from_cwd():
    """現在のディレクトリから自分のエージェント情報を取得"""
    cwd = Path.cwd()
    project_root = find_project_root(cwd)
    
    if not project_root:
        return None
    
    # プロジェクトルートからの相対パス
    try:
        relative_dir = str(cwd.relative_to(project_root))
        if relative_dir == ".":
            relative_dir = ""
    except ValueError:
        relative_dir = str(cwd)
    
    table_file = project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
    
    if table_file.exists():
        with open(table_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                entry = json.loads(line)
                # working_dirでマッチング
                if entry.get('working_dir') == relative_dir:
                    return entry
    
    return None


def get_required_files(agent_id):
    """エージェントIDから必須ファイルリストを生成"""
    # 共通の必須ファイル
    common_files = [
        "CLAUDE.md",
        "Agent-shared/directory_pane_map.txt"
    ]
    
    # 役割を抽出
    role = agent_id.split('.')[0].rstrip('0123456789') if agent_id else ''
    
    role_files = {
        "PM": ["instructions/PM.md", "_remote_info/", "Agent-shared/strategies/auto_tuning/typical_hpc_code.md", "Agent-shared/strategies/auto_tuning/evolutional_flat_dir.md"],
        "SE": ["instructions/SE.md", "Agent-shared/change_log/changelog_analysis_template.py"],
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
1. 全エージェントの進捗確認（SE、PG、CDの巡回）
2. directory_pane_map.txtの更新確認
3. 予算管理（pjstatでポイント確認）
4. 停滞エージェントへの介入
5. リソース再配分の検討

特に最近、進捗確認を行っていないエージェントを優先すること。
"""
    
    elif agent_id.startswith("SE"):
        reason += """【SEの並行タスク】
1. 各PGのChangeLog.md更新状況の監視
2. telemetry/context_usage_monitor.pyでコンテキスト使用状況確認
3. SOTA更新履歴のグラフ生成（Agent-shared/log_analyzer.py）
4. ジョブ実行結果待ち状態の確認
5. visible_path_PG*.txtの更新

"""
    
    elif agent_id.startswith("PG"):
        reason += """【PGの定期タスク】
1. ChangeLog.mdの更新とSOTA管理
2. SSH/SFTPセッションの状態確認（Desktop Commander利用）
3. ジョブキューの状態確認（squeue等）
4. コンパイル警告の解析と修正
5. /resultsディレクトリの整理
6. 新しい最適化手法の実装

性能向上の余地がある限り、継続的に最適化を進めてください。
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
        
        # デバッグ情報をファイルに出力（開発時のみ）
        # debug_file = Path("/tmp/vibecodehpc_stop_hook_debug.log")
        # with open(debug_file, 'a') as f:
        #     f.write(f"\n[{datetime.now()}] Stop hook called\n")
        #     f.write(f"session_id: {session_id}\n")
        #     f.write(f"stop_hook_active: {stop_hook_active}\n")
        
        # 自分のエージェント情報を取得（session_idは使わずcwdで判定）
        agent_info = get_agent_info_from_cwd()
        
        # デバッグ情報追加
        # if debug_file.exists():
        #     with open(debug_file, 'a') as f:
        #         f.write(f"agent_info: {agent_info}\n")
        
        if agent_info:
            # ポーリング型エージェントの場合は停止をブロック
            reason = generate_block_reason(agent_info, stop_hook_active)
            
            if reason:  # stop_hook_activeでない場合のみ
                # 方法1: 終了コード2でstderrに出力（推奨）
                print(reason, file=sys.stderr)
                sys.exit(2)
                
                # 方法2: JSON出力を使う場合（コメントアウト）
                # output = {
                #     "decision": "block",
                #     "reason": reason
                # }
                # print(json.dumps(output, ensure_ascii=False))
                # sys.exit(0)
        
        # 通常終了
        sys.exit(0)
        
    except Exception:
        # エラーは静かに処理
        sys.exit(0)


if __name__ == "__main__":
    main()