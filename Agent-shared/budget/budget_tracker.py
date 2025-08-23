#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ステートレス予算集計システム
ChangeLog.mdから直接時刻情報を読み取って集計
"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys


def find_project_root(start_path):
    """プロジェクトルート（VibeCodeHPC-jp）を探す"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


class BudgetTracker:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.rates = self.load_rates()
        
    def load_rates(self) -> Dict:
        """リソースグループごとのレート設定"""
        # デフォルト設定（不老TypeII）
        rates = {
            'cx-share': {'gpu': 1, 'rate': 0.007},
            'cx-interactive': {'gpu': 1, 'rate': 0.007},
            'cx-debug': {'gpu': 1, 'rate': 0.007},
            'cx-single': {'gpu': 4, 'rate': 0.007},
            'cx-small': {'gpu': 4, 'rate': 0.007},
            'cx-middle': {'gpu': 4, 'rate': 0.007},
            'cx-large': {'gpu': 4, 'rate': 0.007},
            'cx-middle2': {'gpu': 4, 'rate': 0.014},  # 2倍レート
            'cxgfs-small': {'gpu': 4, 'rate': 0.007},
            'cxgfs-middle': {'gpu': 4, 'rate': 0.007},
        }
        
        # node_resource_groups.mdから追加情報を読み込み（将来実装）
        # config_path = self.project_root / "_remote_info/flow/node_resource_groups.md"
        
        return rates
    
    def extract_jobs(self) -> List[Dict]:
        """全ChangeLog.mdからジョブ情報を抽出"""
        all_jobs = []
        
        for changelog in self.project_root.glob('**/ChangeLog.md'):
            # Agent-sharedは除外
            if 'Agent-shared' in str(changelog) or '.git' in str(changelog):
                continue
                
            jobs = self.parse_changelog(changelog)
            all_jobs.extend(jobs)
            
        return all_jobs
    
    def parse_changelog(self, changelog_path: Path) -> List[Dict]:
        """ChangeLog.mdからジョブ情報を抽出"""
        jobs = []
        
        try:
            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return jobs
        
        # バージョンエントリごとに処理
        version_pattern = r'### v(\d+\.\d+\.\d+)(.*?)(?=###|\Z)'
        
        for match in re.finditer(version_pattern, content, re.DOTALL):
            version, section = match.groups()
            
            # jobセクションを探す
            job_match = re.search(r'- \[.\] \*\*job\*\*(.*?)(?=- \[.\] \*\*|\Z)', section, re.DOTALL)
            if not job_match:
                continue
                
            job_section = job_match.group(1)
            
            # 必須フィールドを抽出
            job_info = {
                'version': version,
                'path': str(changelog_path),
                'job_id': self.extract_field(job_section, 'id'),
                'resource_group': self.extract_field(job_section, 'resource_group'),
                'start_time': self.extract_field(job_section, 'start_time'),
                'end_time': self.extract_field(job_section, 'end_time'),
                'cancelled_time': self.extract_field(job_section, 'cancelled_time'),
                'runtime_sec': self.extract_field(job_section, 'runtime_sec'),
                'status': self.extract_field(job_section, 'status'),
            }
            
            # 有効なジョブのみ追加
            if job_info['job_id'] and job_info['resource_group']:
                # runtime_secが無い場合は計算
                if not job_info['runtime_sec'] and job_info['start_time'] and job_info['end_time']:
                    try:
                        start = datetime.fromisoformat(job_info['start_time'].replace('Z', '+00:00'))
                        end = datetime.fromisoformat(job_info['end_time'].replace('Z', '+00:00'))
                        job_info['runtime_sec'] = str(int((end - start).total_seconds()))
                    except:
                        pass
                        
                jobs.append(job_info)
                
        return jobs
    
    def extract_field(self, text: str, field: str) -> str:
        """フィールド値を抽出"""
        pattern = rf'- {field}:\s*`([^`]*)`'
        match = re.search(pattern, text)
        return match.group(1) if match else None
    
    def calculate_timeline(self, jobs: List[Dict]) -> List[Tuple[datetime, float]]:
        """イベントベースで予算消費を計算"""
        events = []
        
        # プロジェクト開始時刻
        start_file = self.project_root / "Agent-shared/project_start_time.txt"
        if start_file.exists():
            try:
                project_start = datetime.fromisoformat(
                    start_file.read_text().strip().replace('Z', '+00:00')
                )
            except:
                project_start = datetime.utcnow() - timedelta(hours=1)
        else:
            project_start = datetime.utcnow() - timedelta(hours=1)
        
        # 各ジョブからイベント生成
        for job in jobs:
            if not job.get('start_time'):
                continue
                
            # 終了時刻の決定
            end_time_str = job.get('end_time') or job.get('cancelled_time')
            if not end_time_str:
                # 実行中の場合は現在時刻を使用
                if job.get('status') in ['running', 'pending']:
                    end_time_str = datetime.utcnow().isoformat() + 'Z'
                else:
                    continue
            
            try:
                start_time = datetime.fromisoformat(job['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except:
                continue
            
            # レート計算
            resource_group = job.get('resource_group', 'cx-small')
            rate_info = self.rates.get(resource_group, {'gpu': 4, 'rate': 0.007})
            points_per_sec = rate_info['rate'] * rate_info['gpu']
            
            events.append({
                'time': start_time,
                'type': 'start',
                'rate': points_per_sec,
                'job': job
            })
            events.append({
                'time': end_time,
                'type': 'end',
                'rate': points_per_sec,
                'job': job
            })
        
        # 時刻でソート
        events.sort(key=lambda x: x['time'])
        
        # タイムライン生成
        timeline = [(project_start, 0.0)]
        current_rate = 0.0
        total_points = 0.0
        last_time = project_start
        
        for event in events:
            # 前のイベントからの消費を計算
            duration = (event['time'] - last_time).total_seconds()
            if duration > 0:
                total_points += current_rate * duration
            
            timeline.append((event['time'], total_points))
            
            # レート更新
            if event['type'] == 'start':
                current_rate += event['rate']
            else:
                current_rate -= event['rate']
                
            last_time = event['time']
        
        # 現在実行中のジョブがある場合
        if current_rate > 0:
            now = datetime.utcnow()
            duration = (now - last_time).total_seconds()
            if duration > 0:
                total_points += current_rate * duration
            timeline.append((now, total_points))
            
        return timeline
    
    def generate_report(self) -> Dict:
        """レポート生成"""
        jobs = self.extract_jobs()
        timeline = self.calculate_timeline(jobs)
        
        # 現在の総消費量
        current_total = timeline[-1][1] if timeline else 0
        
        # スナップショット保存
        snapshot_dir = self.project_root / 'Agent-shared/budget/snapshots'
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')
        
        # レポート作成
        report = {
            'timestamp': timestamp,
            'total_points': current_total,
            'job_count': len([j for j in jobs if j.get('start_time')]),
            'running_jobs': len([j for j in jobs if j.get('status') == 'running']),
            'timeline_points': len(timeline),
        }
        
        # JSON保存
        report_full = {
            **report,
            'jobs': jobs,
            'timeline': [(t.isoformat(), p) for t, p in timeline]
        }
        
        with open(snapshot_dir / f'budget_{timestamp}.json', 'w') as f:
            json.dump(report_full, f, indent=2, default=str)
        
        with open(snapshot_dir / 'latest.json', 'w') as f:
            json.dump(report_full, f, indent=2, default=str)
        
        return report
    
    def print_summary(self):
        """簡易サマリー表示"""
        jobs = self.extract_jobs()
        timeline = self.calculate_timeline(jobs)
        
        total = timeline[-1][1] if timeline else 0
        running = len([j for j in jobs if j.get('status') == 'running'])
        completed = len([j for j in jobs if j.get('status') == 'completed'])
        
        print(f"=== 予算集計サマリー ===")
        print(f"総消費: {total:.1f} ポイント")
        print(f"ジョブ数: 完了={completed}, 実行中={running}")
        
        # 予算に対する割合（仮定値）
        budget_limits = {'最低': 1000, '目安': 2500, '上限': 5000}
        for label, limit in budget_limits.items():
            percentage = (total / limit * 100) if limit > 0 else 0
            print(f"{label}: {percentage:.1f}%")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='予算集計システム')
    parser.add_argument('--summary', action='store_true', help='簡易サマリー表示')
    parser.add_argument('--report', action='store_true', help='詳細レポート生成')
    parser.add_argument('--json', action='store_true', help='JSON形式で出力')
    
    args = parser.parse_args()
    
    # プロジェクトルートを探す
    project_root = find_project_root(Path.cwd())
    if not project_root:
        print("ERROR: プロジェクトルートが見つかりません", file=sys.stderr)
        sys.exit(1)
    
    tracker = BudgetTracker(project_root)
    
    if args.summary:
        tracker.print_summary()
    elif args.json:
        report = tracker.generate_report()
        print(json.dumps(report, indent=2))
    else:
        report = tracker.generate_report()
        print(f"レポート生成完了: {report['total_points']:.1f} ポイント消費")
        print(f"詳細: Agent-shared/budget/snapshots/latest.json")


if __name__ == "__main__":
    main()