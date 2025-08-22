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
VibeCodeHPC Stop Hook for SOLO Agent
シングルエージェント用 - 時間管理と継続タスク提示
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta


def find_project_root(start_path):
    """プロジェクトルート（VibeCodeHPC-jp）を探す"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def get_stop_count():
    """現在のディレクトリのstop_count.txtから回数を取得"""
    stop_count_file = Path.cwd() / ".claude" / "hooks" / "stop_count.txt"
    
    if stop_count_file.exists():
        try:
            return int(stop_count_file.read_text().strip())
        except:
            return 0
    return 0


def increment_stop_count():
    """stop_count.txtをインクリメント"""
    hooks_dir = Path.cwd() / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    stop_count_file = hooks_dir / "stop_count.txt"
    current_count = get_stop_count()
    new_count = current_count + 1
    
    stop_count_file.write_text(str(new_count))
    return new_count


def get_elapsed_time():
    """プロジェクト開始からの経過時間を取得"""
    project_root = find_project_root(Path.cwd())
    if not project_root:
        return None
    
    start_time_file = project_root / "Agent-shared" / "project_start_time.txt"
    if not start_time_file.exists():
        return None
    
    try:
        start_time_str = start_time_file.read_text().strip()
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        current_time = datetime.now(start_time.tzinfo)
        elapsed = current_time - start_time
        return elapsed
    except:
        return None


def get_stop_threshold():
    """SOLOエージェントのSTOP回数閾値を返す"""
    project_root = find_project_root(Path.cwd())
    if project_root:
        threshold_file = project_root / "Agent-shared" / "stop_thresholds.json"
        if threshold_file.exists():
            try:
                with open(threshold_file, 'r') as f:
                    config = json.load(f)
                    thresholds = config.get('thresholds', {})
                    
                    if 'SOLO' in thresholds:
                        return thresholds['SOLO']
            except:
                pass
    
    # デフォルト値（シングルエージェントは長めに設定）
    return 100


def format_elapsed_time(elapsed):
    """経過時間を読みやすい形式でフォーマット"""
    if not elapsed:
        return "不明"
    
    total_seconds = int(elapsed.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}時間{minutes}分"
    else:
        return f"{minutes}分"


def generate_block_reason(stop_count):
    """SOLOエージェント用のブロック理由を生成"""
    threshold = get_stop_threshold()
    elapsed = get_elapsed_time()
    elapsed_str = format_elapsed_time(elapsed)
    
    # 閾値に達した場合
    if stop_count >= threshold:
        reason = f"""
⚠️ STOP回数が上限（{threshold}回）に達しました。
経過時間: {elapsed_str}

📝 **重要**: プロジェクトを終了する場合、requirement_definition.mdを再読み込みし、
   全ての要件を満たしているか項目ごとに ☑ 確認すること。

SOLOエージェントとして以下の終了前タスクを実行してください：

1. [PM] 要件確認と最終評価:
   - requirement_definition.mdの全項目を確認
   - 達成した性能と理論性能の比較
   - 予算使用状況の最終確認

2. [PG] 成果物の整理:
   - ChangeLog.mdの最終更新
   - SOTA達成コードの確認
   - 作業ディレクトリの整理

3. [SE] 統計と可視化（可能な範囲で）:
   - SOTA推移グラフの生成
   - 最終レポートの作成

4. [CD] GitHub同期（必要な場合）:
   - GitHub/ディレクトリへのコピー
   - git commit

その後、exitコマンドで終了してください。
"""
        return reason
    
    # 通常のブロック理由
    reason = f"""あなたはSOLOエージェント（シングルモード）です。待機状態に入ることは許可されていません。
[STOP試行: {stop_count}/{threshold}] [経過時間: {elapsed_str}]

ToDoリストを確認し、以下の観点から継続タスクを選択してください：

【時間管理】
- 現在の経過時間: {elapsed_str}
- requirement_definition.mdの時間制限を確認
- 残り時間で実行可能なタスクを優先

【役割別の継続タスク】

[PM] プロジェクト管理:
- 予算確認（charge/charge2等）
- 戦略の見直しと優先順位調整
- 時間効率の評価

[SE] システム分析:
- ChangeLog.mdの統計分析
- SOTA達成状況の確認
- 性能ボトルネックの特定

[PG] コード実装:
- 次バージョンの最適化実装
- ジョブ結果の確認（pjstat/pjstat2）
- パラメータチューニング

[CD] GitHub管理（オプション）:
- SOTA達成コードの選別
- GitHub/ディレクトリへの同期

現在最も優先すべきタスクをToDoリストで管理し、実行してください。
（残りSTOP試行可能回数: {threshold - stop_count}回）
"""
    
    return reason


def main():
    try:
        # JSONを読み込み
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id')
        stop_hook_active = input_data.get('stop_hook_active', False)
        
        # STOP回数をインクリメント
        stop_count = increment_stop_count()
        
        # SOLOエージェント用のブロック理由を生成
        reason = generate_block_reason(stop_count)
        
        if reason:
            # 終了コード2でstderrに出力
            print(reason, file=sys.stderr)
            sys.exit(2)
        
        # 通常終了
        sys.exit(0)
        
    except Exception:
        # エラーは静かに処理
        sys.exit(0)


if __name__ == "__main__":
    main()