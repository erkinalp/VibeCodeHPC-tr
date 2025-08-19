#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "matplotlib",
#     "numpy",
# ]
# ///

"""
VibeCodeHPC SOTA比較グラフ生成
マルチエージェント vs シングルエージェントの性能比較
"""

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import numpy as np

# グラフスタイル設定
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

class SOTAComparison:
    """SOTA性能比較クラス"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.output_dir = project_root / "User-shared" / "visualizations"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_changelog(self, changelog_path: Path) -> List[Dict]:
        """ChangeLog.mdをパースして性能データを抽出"""
        if not changelog_path.exists():
            return []
        
        content = changelog_path.read_text(encoding='utf-8')
        entries = []
        
        # バージョンごとのエントリをパース（例: ### v1.0.0）
        version_pattern = r'### v(\d+\.\d+\.\d+)'
        result_pattern = r'\*\*結果\*\*: .*?`([\d.]+)\s*(GFLOPS|TFLOPS|ms|sec)`'
        # 生成時刻のパターン（新形式と旧形式の両方に対応）
        time_pattern = r'\*\*生成時刻\*\*:\s*`(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)`'
        old_time_pattern = r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]'
        
        versions = re.finditer(version_pattern, content)
        
        for match in versions:
            version = match.group(1)
            # バージョンセクションの内容を取得
            start = match.end()
            next_version = re.search(version_pattern, content[start:])
            end = start + next_version.start() if next_version else len(content)
            section = content[start:end]
            
            # 結果を抽出
            result_match = re.search(result_pattern, section)
            if result_match:
                value = float(result_match.group(1))
                unit = result_match.group(2)
                
                # 時刻を抽出（新形式優先、なければ旧形式）
                time_match = re.search(time_pattern, section)
                if not time_match:
                    time_match = re.search(old_time_pattern, section)
                timestamp = time_match.group(1) if time_match else None
                
                entries.append({
                    'version': version,
                    'value': value,
                    'unit': unit,
                    'timestamp': timestamp
                })
        
        return entries
    
    def collect_all_sota_data(self) -> Dict[str, List[Dict]]:
        """全てのChangeLog.mdからSOTAデータを収集"""
        sota_data = {
            'multi_agent': [],
            'single_agent': []
        }
        
        # マルチエージェントのデータ収集
        for changelog in self.project_root.rglob('ChangeLog.md'):
            # GitHubディレクトリは除外
            if 'GitHub' in str(changelog):
                continue
            
            entries = self.parse_changelog(changelog)
            if entries:
                # エージェント種別を判定（ディレクトリ構造から）
                if 'single_agent' in str(changelog).lower():
                    sota_data['single_agent'].extend(entries)
                else:
                    sota_data['multi_agent'].extend(entries)
        
        return sota_data
    
    def generate_comparison_graph(self, x_axis='count'):
        """比較グラフを生成
        
        Args:
            x_axis: 'count'（反復回数）または 'time'（時間）
        """
        sota_data = self.collect_all_sota_data()
        
        if not sota_data['multi_agent'] and not sota_data['single_agent']:
            print("⚠️  No SOTA data found")
            return
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # データを正規化（GFLOPS単位に統一）
        for mode in ['multi_agent', 'single_agent']:
            if not sota_data[mode]:
                continue
            
            # 単位を統一
            normalized_data = []
            for entry in sota_data[mode]:
                value = entry['value']
                if entry['unit'] == 'TFLOPS':
                    value *= 1000  # TFLOPS → GFLOPS
                elif entry['unit'] in ['ms', 'sec']:
                    # 実行時間の場合は逆数を取って性能指標に変換
                    if entry['unit'] == 'ms':
                        value = 1000.0 / value if value > 0 else 0
                    else:  # sec
                        value = 1.0 / value if value > 0 else 0
                
                normalized_data.append({
                    'version': entry['version'],
                    'value': value,
                    'timestamp': entry['timestamp']
                })
            
            if x_axis == 'count':
                # 反復回数ベース
                x_values = list(range(1, len(normalized_data) + 1))
                y_values = [d['value'] for d in normalized_data]
            else:  # time
                # 時間ベース（最初のエントリからの経過時間）
                if normalized_data[0]['timestamp']:
                    start_time = datetime.fromisoformat(normalized_data[0]['timestamp'].replace('Z', '+00:00'))
                    x_values = []
                    y_values = []
                    for d in normalized_data:
                        if d['timestamp']:
                            t = datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00'))
                            elapsed = (t - start_time).total_seconds() / 60  # 分単位
                            x_values.append(elapsed)
                            y_values.append(d['value'])
                else:
                    # タイムスタンプがない場合は反復回数を使用
                    x_values = list(range(1, len(normalized_data) + 1))
                    y_values = [d['value'] for d in normalized_data]
            
            # SOTAのみをプロット（単調増加）
            sota_x = []
            sota_y = []
            max_value = 0
            for x, y in zip(x_values, y_values):
                if y > max_value:
                    sota_x.append(x)
                    sota_y.append(y)
                    max_value = y
            
            # ラベル設定
            label = 'Multi-Agent' if mode == 'multi_agent' else 'Single-Agent'
            color = 'blue' if mode == 'multi_agent' else 'red'
            
            # 階段状のグラフ
            if sota_x and sota_y:
                ax.step(sota_x, sota_y, where='post', marker='o', markersize=5,
                       label=f'{label} (Max: {max_value:.1f} GFLOPS)', 
                       color=color, linewidth=2)
        
        # グラフ装飾
        if x_axis == 'count':
            ax.set_xlabel('Iteration Count')
        else:
            ax.set_xlabel('Time (minutes from start)')
        
        ax.set_ylabel('Performance (GFLOPS equivalent)')
        ax.set_title('SOTA Performance Comparison: Multi-Agent vs Single-Agent')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # ファイル保存
        output_path = self.output_dir / f"sota_comparison_{x_axis}.png"
        plt.savefig(output_path, dpi=120, bbox_inches='tight')
        plt.close()
        
        print(f"✅ SOTA comparison graph saved: {output_path}")
    
    def generate_all_comparisons(self):
        """全ての比較グラフを生成"""
        self.generate_comparison_graph('count')
        self.generate_comparison_graph('time')
        
        # サマリーレポート生成
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """比較サマリーレポートを生成"""
        sota_data = self.collect_all_sota_data()
        
        report_path = self.output_dir / "sota_comparison_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# SOTA Performance Comparison Report\n\n")
            f.write(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
            
            f.write("## Summary\n\n")
            
            # 各モードの最高性能を計算
            for mode in ['multi_agent', 'single_agent']:
                if sota_data[mode]:
                    max_entry = max(sota_data[mode], key=lambda x: x['value'])
                    mode_label = 'Multi-Agent' if mode == 'multi_agent' else 'Single-Agent'
                    f.write(f"### {mode_label}\n")
                    f.write(f"- **Best Performance**: {max_entry['value']:.2f} {max_entry['unit']}\n")
                    f.write(f"- **Version**: {max_entry['version']}\n")
                    f.write(f"- **Total Iterations**: {len(sota_data[mode])}\n\n")
            
            f.write("## Visualizations\n\n")
            f.write("- [SOTA Comparison by Count](sota_comparison_count.png)\n")
            f.write("- [SOTA Comparison by Time](sota_comparison_time.png)\n")
        
        print(f"✅ Summary report saved: {report_path}")


def main():
    """メイン処理"""
    project_root = Path(__file__).parent.parent
    
    comparison = SOTAComparison(project_root)
    comparison.generate_all_comparisons()


if __name__ == "__main__":
    main()