#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook for SOLO Agent
シングルAjan用 - 時間Yönetimと継続タスク提示
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta


def find_project_root(start_path):
    """Projeルート（VibeCodeHPC-jp）を探す"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def get_stop_count():
    """現在のDizinのstop_count.txtから回数をAlma"""
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
    """Proje開始からの経過時間をAlma"""
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
    """SOLOAjanのSTOP回数閾値を返す"""
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
    
    # デフォルト値（シングルAjanは長めにAyar）
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
    """SOLOAjan用のブロック理由をÜretim"""
    threshold = get_stop_threshold()
    elapsed = get_elapsed_time()
    elapsed_str = format_elapsed_time(elapsed)
    
    # 閾値に達した場合
    if stop_count >= threshold:
        reason = f"""
⚠️ STOP回数が上限（{threshold}回）に達しました。
経過時間: {elapsed_str}

📝 **Önemli**: Projeを終了する場合、requirement_definition.mdを再Okumaし、
   全ての要件を満たしているか項目ごとに ☑ Kontrolすること。

SOLOAjanとして以下の終了前タスクをYürütmeしてください：

1. [PM] 要件Kontrolと最終評価:
   - requirement_definition.mdの全項目をKontrol
   - 達成したPerformansと理論Performansの比較
   - Bütçe使用状況の最終Kontrol

2. [PG] 成果物の整理:
   - ChangeLog.mdの最終Güncelleme
   - SOTA達成コードのKontrol
   - 作業Dizinの整理

3. [SE] İstatistikとGörselleştirme（可能な範囲で）:
   - SOTA推移GrafikのÜretim
   - 最終レポートのOluşturma

4. [CD] GitHub同期（必要な場合）:
   - GitHub/Dizinへのコピー
   - git commit

その後、exitKomutで終了してください。
"""
        return reason
    
    # 通常のブロック理由
    reason = f"""あなたはSOLOAjan（シングルモード）です。待機状態に入ることは許可されていません。
[STOP試行: {stop_count}/{threshold}] [経過時間: {elapsed_str}]

【必須Dosyaの再Okuma】
以下のDosyaから最新状態をKontrolしてください（未読または10行のみ読んだものを優先）：
- CLAUDE.md
- instructions/SOLO.md
- requirement_definition.md
- Agent-shared/directory_pane_map.txt
- Agent-shared/strategies/auto_tuning/typical_hpc_code.md
- Agent-shared/budget/budget_history.md
- Agent-shared/sota/sota_visualizer.py（SOTAGörselleştirme必須タスク）
- telemetry/context_usage_monitor.py（コンテキストİzleme必須タスク）
- Agent-shared/ssh_sftp_guide.md（SSH/SFTP接続・Yürütmeガイド）
- hardware_info.md（理論Performans目標）
- 現在のDizinのChangeLog.md

【必須の非同期タスク（優先順）】
1. **最優先: コンテキスト使用率Görselleştirme**（auto-compact防止）
   python3 telemetry/context_usage_monitor.py --graph-type overview
   （30分ごと、30/60/90/120/180分でマイルストーンKaydetme）

2. **優先: SOTAPerformansGrafik**（成果Görselleştirme）
   for level in project family hardware local; do
       python3 Agent-shared/sota/sota_visualizer.py --level $level
   done

3. **通常: Bütçe推移**（可能な場合）
   python3 Agent-shared/budget/budget_tracker.py --graph

【役割別の継続タスク】

[PG] コード実装:
- 次バージョンのOptimizasyon実装
- ジョブ結果のKontrol（pjstat/pjstat2）
- パラメータチューニング

[CD] GitHub継続的同期:
- SOTA達成コードの定期commit（一回きりではない）
- ChangeLog.mdGüncellemeの同期

現在最も優先すべきタスクをToDoリストでYönetimし、Yürütmeしてください。
（残りSTOP試行可能回数: {threshold - stop_count}回）
"""
    
    return reason


def main():
    try:
        # JSONをOkuma
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id')
        stop_hook_active = input_data.get('stop_hook_active', False)
        
        # STOP回数をインクリメント
        stop_count = increment_stop_count()
        
        # SOLOAjan用のブロック理由をÜretim
        reason = generate_block_reason(stop_count)
        
        if reason:
            # 終了コード2でstderrに出力
            print(reason, file=sys.stderr)
            sys.exit(2)
        
        # 通常終了
        sys.exit(0)
        
    except Exception:
        # Hataは静かにİşleme
        sys.exit(0)


if __name__ == "__main__":
    main()