#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "matplotlib",
#     "numpy",
#     "pandas",
# ]
# ///

"""
VibeCodeHPC SOTA可視化ツール
4階層（local/family/hardware/project）のSOTA推移をグラフ化
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

class SOTAVisualizer:
    """SOTA性能推移の可視化クラス"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.base_output_dir = project_root / "User-shared" / "visualizations" / "sota"
        
        # 階層別の出力ディレクトリ
        self.output_dirs = {
            'project': self.base_output_dir / 'project',
            'hardware': self.base_output_dir / 'hardware', 
            'family': self.base_output_dir / 'family',
            'local': self.base_output_dir / 'local',
            'comparison': self.base_output_dir / 'comparison'
        }
        for dir_path in self.output_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # デフォルト設定
        self.theoretical_perf = None  # 理論性能（hardware_info.mdから読み取る）
        self.use_log_scale = False
        self.show_theoretical = False
        self.x_axis_type = 'time'  # 'time' or 'count'
        
    def parse_changelog_entry(self, content: str) -> List[Dict]:
        """ChangeLog.mdから性能データを抽出"""
        entries = []
        
        # パターン定義
        version_pattern = r'### v(\d+\.\d+\.\d+)'
        time_pattern = r'\*\*生成時刻\*\*:\s*`(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)`'
        result_patterns = [
            r'\*\*結果\*\*:.*?`([\d.]+)\s*(GFLOPS|TFLOPS|GB/s|ms|sec|fps)`',
            r'performance:\s*`([\d.]+)`.*?unit:\s*`([^`]+)`',
        ]
        
        # バージョンごとに処理
        for version_match in re.finditer(version_pattern, content):
            version = version_match.group(1)
            start = version_match.end()
            
            # 次のバージョンまでのセクションを取得
            next_match = re.search(version_pattern, content[start:])
            end = start + next_match.start() if next_match else len(content)
            section = content[start:end]
            
            # 時刻を抽出
            time_match = re.search(time_pattern, section)
            timestamp = time_match.group(1) if time_match else None
            
            # 結果を抽出
            for pattern in result_patterns:
                result_match = re.search(pattern, section)
                if result_match:
                    value = float(result_match.group(1))
                    unit = result_match.group(2)
                    
                    # 単位を正規化（TFLOPS→GFLOPS変換など）
                    if unit == 'TFLOPS':
                        value *= 1000
                        unit = 'GFLOPS'
                    elif unit in ['ms', 'sec']:
                        # 実行時間の場合は逆数を取って性能指標に
                        if unit == 'ms':
                            value = 1000.0 / value if value > 0 else 0
                        else:
                            value = 1.0 / value if value > 0 else 0
                        unit = 'throughput'
                    
                    entries.append({
                        'version': version,
                        'timestamp': timestamp,
                        'value': value,
                        'unit': unit
                    })
                    break
        
        return entries
    
    def collect_sota_data(self) -> Dict[str, Dict]:
        """全階層のSOTAデータを収集"""
        sota_data = {
            'local': {},     # PGごと
            'family': {},    # ミドルウェア階層ごと
            'hardware': {},  # ハードウェア構成ごと
            'project': []    # プロジェクト全体
        }
        
        # ChangeLog.mdを全探索
        for changelog_path in self.project_root.rglob('ChangeLog.md'):
            # GitHubディレクトリは除外
            if 'GitHub' in str(changelog_path):
                continue
            
            content = changelog_path.read_text(encoding='utf-8')
            entries = self.parse_changelog_entry(content)
            
            if not entries:
                continue
            
            # パスから階層情報を抽出
            rel_path = changelog_path.relative_to(self.project_root)
            parts = rel_path.parts
            
            # PGエージェントIDを推定
            agent_id = None
            for part in parts:
                if re.match(r'PG\d+\.\d+\.\d+', part):
                    agent_id = part
                    break
            
            if not agent_id:
                # ディレクトリ名からエージェントIDを推定
                parent = changelog_path.parent.name
                if 'OpenMP' in parent or 'MPI' in parent or 'CUDA' in parent:
                    agent_id = f"PG_{parent}"
            
            # Local SOTA
            if agent_id:
                if agent_id not in sota_data['local']:
                    sota_data['local'][agent_id] = []
                sota_data['local'][agent_id].extend(entries)
            
            # Family SOTA（ミドルウェア階層）
            middleware = None
            for part in parts:
                if any(tech in part for tech in ['OpenMP', 'MPI', 'CUDA', 'OpenACC']):
                    middleware = part
                    break
            
            if middleware:
                if middleware not in sota_data['family']:
                    sota_data['family'][middleware] = []
                sota_data['family'][middleware].extend(entries)
            
            # Hardware SOTA
            hardware_path = None
            for i, part in enumerate(parts):
                if 'hardware_info.md' in [p.name for p in (self.project_root / Path(*parts[:i+1])).glob('*')]:
                    hardware_path = '/'.join(parts[:i+1])
                    break
            
            if hardware_path:
                if hardware_path not in sota_data['hardware']:
                    sota_data['hardware'][hardware_path] = []
                sota_data['hardware'][hardware_path].extend(entries)
            
            # Project SOTA（全エントリ）
            sota_data['project'].extend(entries)
        
        return sota_data
    
    def extract_sota_progression(self, entries: List[Dict]) -> Tuple[List, List, List]:
        """エントリからSOTA更新の推移を抽出"""
        if not entries:
            return [], [], []
        
        # タイムスタンプでソート
        sorted_entries = sorted(entries, key=lambda x: x['timestamp'] or '0')
        
        # 最初のタイムスタンプからの経過時間を計算
        start_time = None
        times = []
        values = []
        versions = []
        
        max_value = 0
        for entry in sorted_entries:
            if entry['value'] > max_value:  # SOTA更新時のみ記録
                max_value = entry['value']
                values.append(entry['value'])
                versions.append(entry['version'])
                
                if self.x_axis_type == 'time' and entry['timestamp']:
                    if not start_time:
                        start_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    current_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    elapsed_minutes = (current_time - start_time).total_seconds() / 60
                    times.append(elapsed_minutes)
                else:
                    # カウントベース
                    times.append(len(times))
        
        return times, values, versions
    
    def load_hardware_info(self, hardware_path: Path) -> Optional[float]:
        """hardware_info.mdから理論性能を読み取る"""
        info_path = hardware_path / 'hardware_info.md'
        if not info_path.exists():
            return None
        
        content = info_path.read_text(encoding='utf-8')
        
        # 理論性能のパターン
        patterns = [
            r'理論性能[：:]\s*([\d.]+)\s*(GFLOPS|TFLOPS)',
            r'Peak Performance[：:]\s*([\d.]+)\s*(GFLOPS|TFLOPS)',
            r'理論演算性能[：:]\s*([\d.]+)\s*(GFLOPS|TFLOPS)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                if unit == 'TFLOPS':
                    value *= 1000
                return value
        
        return None
    
    def plot_sota_comparison(self, 
                            sota_level: str = 'project',
                            x_axis: str = 'time',
                            log_scale: bool = False,
                            show_theoretical: bool = True,
                            theoretical_ratio: float = 0.1):
        """SOTA推移グラフを生成
        
        Args:
            sota_level: 'local', 'family', 'hardware', 'project'のいずれか
            x_axis: 'time'（経過時間）または 'count'（更新回数）
            log_scale: Y軸を対数スケールにするか
            show_theoretical: 理論性能を表示するか
            theoretical_ratio: 理論性能が不明な場合の上限設定（最高性能の何倍か）
        """
        self.x_axis_type = x_axis
        self.use_log_scale = log_scale
        self.show_theoretical = show_theoretical
        
        # データ収集
        sota_data = self.collect_sota_data()
        
        # グラフ設定
        fig, ax = plt.subplots(figsize=(14, 8))
        
        if sota_level == 'project':
            # プロジェクト全体（1つのグラフ）
            times, values, versions = self.extract_sota_progression(sota_data['project'])
            if times and values:
                ax.step(times, values, where='post', marker='o', 
                       label='Project SOTA', color='blue', linewidth=2)
                
                # 理論性能の表示
                if show_theoretical and values:
                    max_value = max(values)
                    theoretical = self.theoretical_perf or (max_value * (1 + theoretical_ratio))
                    ax.axhline(y=theoretical, color='red', linestyle='--', 
                             label=f'Theoretical Peak ({theoretical:.1f} GFLOPS)')
        
        elif sota_level in ['local', 'family', 'hardware']:
            # 複数のグラフ
            data_dict = sota_data[sota_level]
            colors = plt.cm.tab10(np.linspace(0, 1, min(10, len(data_dict))))
            
            for i, (key, entries) in enumerate(data_dict.items()):
                times, values, versions = self.extract_sota_progression(entries)
                if times and values:
                    color = colors[i % len(colors)]
                    ax.step(times, values, where='post', marker='o',
                           label=f'{key} (Max: {max(values):.1f})',
                           color=color, linewidth=1.5, markersize=4)
        
        # 軸設定
        if x_axis == 'time':
            ax.set_xlabel('Time (minutes from start)')
        else:
            ax.set_xlabel('SOTA Update Count')
        
        ax.set_ylabel('Performance (GFLOPS equivalent)')
        
        if log_scale:
            ax.set_yscale('log')
        
        # グラフ装飾
        ax.set_title(f'SOTA Performance Progression - {sota_level.capitalize()} Level')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # ファイル保存（階層別ディレクトリに）
        filename = f"sota_{sota_level}_{x_axis}"
        if log_scale:
            filename += "_log"
        
        # 適切な出力ディレクトリを選択
        if sota_level in self.output_dirs:
            output_dir = self.output_dirs[sota_level]
        else:
            output_dir = self.base_output_dir
        
        output_path = output_dir / f"{filename}.png"
        
        plt.savefig(output_path, dpi=120, bbox_inches='tight')
        plt.close()
        
        print(f"✅ SOTA graph saved: {output_path}")
        return output_path
    
    def generate_all_graphs(self):
        """全パターンのグラフを生成"""
        levels = ['local', 'family', 'hardware', 'project']
        generated_count = 0
        
        for level in levels:
            # 時間軸・リニアスケール
            self.plot_sota_comparison(level, 'time', False, True)
            generated_count += 1
            # カウント軸・リニアスケール
            self.plot_sota_comparison(level, 'count', False, True)
            generated_count += 1
            # 時間軸・対数スケール
            self.plot_sota_comparison(level, 'time', True, True)
            generated_count += 1
        
        # レポート生成
        self.generate_visualization_report(generated_count)
        
        print(f"✅ All SOTA graphs generated: {generated_count} files")
    
    def generate_visualization_report(self, total_count: int):
        """可視化レポートを自動生成"""
        report_dir = self.project_root / "User-shared" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "sota_visualization_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# SOTA Visualization Report\n\n")
            f.write(f"Generated: {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n")
            
            # 各階層のグラフリンク
            for level_name, level_dir in self.output_dirs.items():
                if level_dir.exists():
                    png_files = list(level_dir.glob("*.png"))
                    if png_files:
                        f.write(f"## {level_name.capitalize()} Level\n\n")
                        for png_file in sorted(png_files):
                            # 相対パス（reportからvisualizationへ）
                            rel_path = Path("../visualizations/sota") / level_name / png_file.name
                            f.write(f"### {png_file.stem}\n")
                            f.write(f"![{png_file.stem}]({rel_path})\n\n")
            
            f.write(f"\n## Summary\n")
            f.write(f"- Total graphs: {total_count}\n")
            f.write(f"- Levels: local, family, hardware, project\n")
            f.write(f"- Variants: time/count axis, linear/log scale\n")
        
        print(f"✅ Report saved: {report_path}")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VibeCodeHPC SOTA Visualizer')
    parser.add_argument('--level', default='project',
                       choices=['local', 'family', 'hardware', 'project', 'all'],
                       help='SOTA level to visualize')
    parser.add_argument('--x-axis', default='time', choices=['time', 'count'],
                       help='X-axis type')
    parser.add_argument('--log-scale', action='store_true',
                       help='Use logarithmic scale for Y-axis')
    parser.add_argument('--no-theoretical', action='store_true',
                       help='Hide theoretical performance line')
    parser.add_argument('--theoretical-ratio', type=float, default=0.1,
                       help='Theoretical performance ratio when unknown')
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    visualizer = SOTAVisualizer(project_root)
    
    if args.level == 'all':
        visualizer.generate_all_graphs()
    else:
        visualizer.plot_sota_comparison(
            sota_level=args.level,
            x_axis=args.x_axis,
            log_scale=args.log_scale,
            show_theoretical=not args.no_theoretical,
            theoretical_ratio=args.theoretical_ratio
        )


if __name__ == "__main__":
    main()