#!/usr/bin/env python3
"""
SOTA可視化の効率化版
- データ収集を1回だけ実行
- 変数を共有して複数のグラフを高速生成
- 同一レベルの4種類（time/count × linear/log）を一括生成
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
import argparse


class EfficientSOTAVisualizer:
    """効率的なSOTA可視化クラス"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.output_dir = project_root / "User-shared" / "visualizations" / "sota"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 共有データ（一度だけ収集）
        self.sota_data = None
        self.theoretical_performance = None
        self.project_start_time = None
        
    def collect_data_once(self) -> Dict[str, Dict]:
        """全データを一度だけ収集して共有"""
        if self.sota_data is not None:
            return self.sota_data
            
        print("📊 Collecting SOTA data from all ChangeLogs...")
        
        # プロジェクト開始時刻を取得
        start_time_file = self.project_root / "Agent-shared" / "project_start_time.txt"
        if start_time_file.exists():
            self.project_start_time = datetime.fromisoformat(
                start_time_file.read_text().strip().replace('Z', '+00:00')
            )
        else:
            self.project_start_time = datetime.now()
        
        # データ構造の初期化
        self.sota_data = {
            'project': {},      # 全体SOTA
            'family': defaultdict(dict),   # ファミリー別
            'hardware': defaultdict(dict),  # ハードウェア別
            'true_hardware': defaultdict(dict),  # 真のハードウェアレベル
            'local': {},        # 各PGのローカルSOTA
            'raw_data': defaultdict(list)  # 生データ（全エントリ）
        }
        
        # ChangeLog.mdファイルを再帰的に検索
        changelog_files = list(self.project_root.rglob("ChangeLog.md"))
        
        for changelog_path in changelog_files:
            relative_path = changelog_path.parent.relative_to(self.project_root)
            path_str = str(relative_path)
            
            # ファミリーとハードウェアの判定
            family_key = self._get_family_key(path_str)
            hardware_key = self._get_hardware_key(path_str)
            true_hw_key = self._get_true_hardware_key(path_str)
            
            # ChangeLogからデータ抽出
            entries = self._parse_changelog(changelog_path)
            
            for entry in entries:
                # 生データを保存
                entry_with_meta = {
                    **entry,
                    'path': path_str,
                    'family': family_key,
                    'hardware': hardware_key,
                    'true_hardware': true_hw_key,
                    'agent_id': self._extract_agent_id(path_str)
                }
                self.sota_data['raw_data'][path_str].append(entry_with_meta)
                
                # 各レベルのSOTA更新
                performance = entry.get('performance', 0)
                if performance > 0:
                    # Project level
                    if 'project' not in self.sota_data['project'] or \
                       performance > self.sota_data['project']['project']['performance']:
                        self.sota_data['project']['project'] = entry_with_meta
                    
                    # Family level
                    if family_key:
                        if family_key not in self.sota_data['family'][family_key] or \
                           performance > self.sota_data['family'][family_key][family_key]['performance']:
                            self.sota_data['family'][family_key][family_key] = entry_with_meta
                    
                    # Hardware level
                    if hardware_key:
                        if hardware_key not in self.sota_data['hardware'][hardware_key] or \
                           performance > self.sota_data['hardware'][hardware_key][hardware_key]['performance']:
                            self.sota_data['hardware'][hardware_key][hardware_key] = entry_with_meta
                    
                    # True hardware level
                    if true_hw_key:
                        if true_hw_key not in self.sota_data['true_hardware'][true_hw_key] or \
                           performance > self.sota_data['true_hardware'][true_hw_key][true_hw_key]['performance']:
                            self.sota_data['true_hardware'][true_hw_key][true_hw_key] = entry_with_meta
                    
                    # Local level (per agent)
                    agent_id = self._extract_agent_id(path_str)
                    if agent_id:
                        if agent_id not in self.sota_data['local'] or \
                           performance > self.sota_data['local'][agent_id]['performance']:
                            self.sota_data['local'][agent_id] = entry_with_meta
        
        # 理論性能の取得
        self._load_theoretical_performance()
        
        print(f"✅ Data collection complete: {len(changelog_files)} ChangeLogs processed")
        return self.sota_data
    
    def generate_level_variants(self, level: str, specific_key: Optional[str] = None):
        """指定レベルの4種類のグラフを効率的に生成"""
        
        # データが未収集なら収集
        if self.sota_data is None:
            self.collect_data_once()
        
        # レベルに応じたデータを取得
        level_data = self._get_level_data(level, specific_key)
        if not level_data:
            print(f"⚠️ No data for level={level}, specific={specific_key}")
            return []
        
        generated_files = []
        
        # 基本データを準備（共通処理）
        x_time_data, y_data, labels = self._prepare_plot_data(level_data, 'time')
        x_count_data, _, _ = self._prepare_plot_data(level_data, 'count')
        
        # 4種類のグラフを生成
        variants = [
            ('time', False),   # time軸・線形
            ('time', True),    # time軸・対数
            ('count', False),  # count軸・線形
            ('count', True),   # count軸・対数（通常不要だが完全性のため）
        ]
        
        for x_axis, log_scale in variants:
            if x_axis == 'count' and log_scale:
                continue  # count軸の対数は意味がないのでスキップ
                
            # プロット用データを選択
            if x_axis == 'time':
                x_data = x_time_data
            else:
                x_data = x_count_data
            
            # グラフ生成
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # データをプロット
            for i, (x, y, label) in enumerate(zip(x_data, y_data, labels)):
                if x and y:  # データが存在する場合のみプロット
                    ax.plot(x, y, marker='o', label=label, linewidth=2)
            
            # 理論性能線を追加
            if self.theoretical_performance and x_axis == 'time':
                self._add_theoretical_line(ax, x_time_data)
            
            # 軸設定
            if log_scale:
                ax.set_yscale('log')
            
            if x_axis == 'time':
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
                plt.xticks(rotation=45)
                ax.set_xlabel('Time (from project start)')
            else:
                ax.set_xlabel('Trial Count')
            
            ax.set_ylabel('Performance (GFLOPS)')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best')
            
            # タイトル設定
            scale_str = 'log' if log_scale else 'linear'
            specific_str = f"_{specific_key}" if specific_key else ""
            title = f"SOTA Comparison - {level.upper()}{specific_str} ({x_axis}, {scale_str})"
            ax.set_title(title)
            
            # ファイル保存
            filename = f"sota_{level}{specific_str}_{x_axis}_{scale_str}.png"
            output_path = self.output_dir / filename
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            generated_files.append(output_path)
            print(f"  ✅ Generated: {filename}")
        
        return generated_files
    
    def generate_all_efficient(self, milestone_minutes: Optional[int] = None):
        """全レベル・全組み合わせを効率的に生成"""
        
        print(f"\n🚀 Efficient SOTA visualization started (milestone={milestone_minutes}min)")
        start_time = datetime.now()
        
        # データを一度だけ収集
        self.collect_data_once()
        
        all_generated = []
        
        # レベルごとに順次生成（データは共有）
        levels_to_generate = [
            ('project', [None]),  # projectは1つ
            ('local', [None]),    # localも1つ（全PG表示）
            ('family', list(self.sota_data['family'].keys())),  # 各ファミリー
            ('hardware', list(self.sota_data['hardware'].keys())),  # 各ハードウェア
        ]
        
        for level, keys in levels_to_generate:
            print(f"\n📈 Generating {level} level graphs...")
            if keys[0] is None:
                # 単一グラフ
                files = self.generate_level_variants(level)
                all_generated.extend(files)
            else:
                # 複数のキーごとにグラフ生成
                for key in keys:
                    files = self.generate_level_variants(level, key)
                    all_generated.extend(files)
        
        # マイルストーン保存（必要な場合）
        if milestone_minutes:
            self._save_milestone_snapshots(all_generated, milestone_minutes)
        
        # 実行時間を計測
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ Efficient generation complete: {len(all_generated)} files in {elapsed:.1f}s")
        print(f"   (Average: {elapsed/len(all_generated):.2f}s per graph)")
        
        return all_generated
    
    def _parse_changelog(self, changelog_path: Path) -> List[Dict]:
        """ChangeLog.mdからエントリを抽出"""
        entries = []
        
        try:
            content = changelog_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            current_entry = {}
            in_details = False
            
            for line in lines:
                # バージョン行
                if line.startswith('### v'):
                    if current_entry and 'performance' in current_entry:
                        entries.append(current_entry.copy())
                    current_entry = {'version': line.replace('### ', '')}
                
                # 結果行からperformance抽出
                elif '**結果**:' in line:
                    import re
                    # GFLOPS値を抽出
                    match = re.search(r'`([\d.]+)\s*GFLOPS`', line)
                    if match:
                        current_entry['performance'] = float(match.group(1))
                
                # 生成時刻
                elif '**生成時刻**:' in line and '`' in line:
                    time_str = line.split('`')[1].split('`')[0]
                    try:
                        current_entry['timestamp'] = datetime.fromisoformat(
                            time_str.replace('Z', '+00:00')
                        )
                    except:
                        pass
            
            # 最後のエントリ
            if current_entry and 'performance' in current_entry:
                entries.append(current_entry)
                
        except Exception as e:
            print(f"⚠️ Error parsing {changelog_path}: {e}")
        
        return entries
    
    def _get_level_data(self, level: str, specific_key: Optional[str]) -> Dict:
        """指定レベルのデータを取得"""
        if level == 'project':
            return self.sota_data['project']
        elif level == 'local':
            return self.sota_data['local']
        elif level == 'family':
            if specific_key:
                return self.sota_data['family'].get(specific_key, {})
            else:
                # 全ファミリーを結合
                result = {}
                for family_data in self.sota_data['family'].values():
                    result.update(family_data)
                return result
        elif level == 'hardware':
            if specific_key:
                return self.sota_data['hardware'].get(specific_key, {})
            else:
                # 全ハードウェアを結合
                result = {}
                for hw_data in self.sota_data['hardware'].values():
                    result.update(hw_data)
                return result
        return {}
    
    def _prepare_plot_data(self, level_data: Dict, x_axis: str) -> Tuple[List, List, List]:
        """プロット用データを準備（共通処理）"""
        x_data = []
        y_data = []
        labels = []
        
        for key, data in level_data.items():
            if x_axis == 'time':
                # 時系列データ
                x = []
                y = []
                for entry in self.sota_data['raw_data'].get(data.get('path', ''), []):
                    if 'timestamp' in entry and 'performance' in entry:
                        elapsed = (entry['timestamp'] - self.project_start_time).total_seconds() / 60
                        x.append(elapsed)
                        y.append(entry['performance'])
                if x and y:
                    x_data.append(x)
                    y_data.append(y)
                    labels.append(key)
            else:
                # カウントベース
                x = []
                y = []
                count = 0
                for entry in self.sota_data['raw_data'].get(data.get('path', ''), []):
                    if 'performance' in entry:
                        count += 1
                        x.append(count)
                        y.append(entry['performance'])
                if x and y:
                    x_data.append(x)
                    y_data.append(y)
                    labels.append(key)
        
        return x_data, y_data, labels
    
    def _load_theoretical_performance(self):
        """理論性能を取得"""
        # hardware_info.mdから理論性能を検索
        hardware_info_files = list(self.project_root.rglob("hardware_info.md"))
        for hw_file in hardware_info_files:
            try:
                content = hw_file.read_text(encoding='utf-8')
                if '理論演算性能' in content or 'GFLOPS' in content:
                    import re
                    match = re.search(r'([\d.]+)\s*GFLOPS', content)
                    if match:
                        self.theoretical_performance = float(match.group(1))
                        print(f"📊 Theoretical performance: {self.theoretical_performance} GFLOPS")
                        break
            except:
                pass
    
    def _add_theoretical_line(self, ax, x_data):
        """理論性能線を追加"""
        if not self.theoretical_performance or not x_data:
            return
            
        # x軸の範囲を取得
        all_x = []
        for x in x_data:
            if x:
                all_x.extend(x)
        
        if all_x:
            min_x = min(all_x)
            max_x = max(all_x)
            
            # 80%と100%の線を追加
            ax.axhline(y=self.theoretical_performance * 0.8, 
                      color='orange', linestyle='--', alpha=0.5, 
                      label=f'Theoretical 80% ({self.theoretical_performance*0.8:.1f} GFLOPS)')
            ax.axhline(y=self.theoretical_performance, 
                      color='red', linestyle='--', alpha=0.5,
                      label=f'Theoretical 100% ({self.theoretical_performance:.1f} GFLOPS)')
    
    def _get_family_key(self, path_str: str) -> Optional[str]:
        """パスからファミリーを判定"""
        # OpenMP, MPI, CUDA, OpenMP_MPI等を検出
        parts = path_str.split('/')
        for part in parts:
            if any(tech in part for tech in ['OpenMP', 'MPI', 'CUDA', 'OpenACC']):
                return part
        return None
    
    def _get_hardware_key(self, path_str: str) -> Optional[str]:
        """パスからハードウェア（コンパイラ）を判定"""
        # gcc, intel等を検出
        parts = path_str.split('/')
        for part in parts:
            if any(comp in part.lower() for comp in ['gcc', 'intel', 'nvcc', 'clang']):
                return part
        return None
    
    def _get_true_hardware_key(self, path_str: str) -> Optional[str]:
        """真のハードウェアレベル（single-node等）を判定"""
        parts = path_str.split('/')
        for part in parts:
            if any(hw in part for hw in ['single-node', 'multi-node', 'gpu-cluster']):
                return part
        return None
    
    def _extract_agent_id(self, path_str: str) -> Optional[str]:
        """パスからエージェントIDを推定"""
        # PG1.1.1形式を検出
        import re
        match = re.search(r'PG\d+\.\d+\.\d+', path_str)
        if match:
            return match.group()
        # パスの最後の要素をエージェントIDとして使用
        return path_str.split('/')[-1] if path_str else None
    
    def _save_milestone_snapshots(self, generated_files: List[Path], milestone_minutes: int):
        """マイルストーンのスナップショットを保存"""
        milestone_dir = self.output_dir / f"milestone_{milestone_minutes}min"
        milestone_dir.mkdir(exist_ok=True)
        
        for file_path in generated_files:
            if file_path.exists():
                import shutil
                dest = milestone_dir / file_path.name
                shutil.copy2(file_path, dest)
        
        print(f"📸 Milestone snapshot saved: {milestone_dir}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Efficient SOTA Visualizer')
    parser.add_argument('--level', choices=['all', 'project', 'family', 'hardware', 'local'],
                       default='all', help='Visualization level')
    parser.add_argument('--specific', help='Specific key for family/hardware level')
    parser.add_argument('--milestone', type=int, help='Milestone minutes for snapshot')
    
    args = parser.parse_args()
    
    # プロジェクトルートを検索
    current = Path.cwd()
    while current != current.parent:
        if (current / "CLAUDE.md").exists():
            project_root = current
            break
        current = current.parent
    else:
        print("❌ Could not find project root (CLAUDE.md)")
        sys.exit(1)
    
    visualizer = EfficientSOTAVisualizer(project_root)
    
    if args.level == 'all':
        visualizer.generate_all_efficient(args.milestone)
    else:
        visualizer.generate_level_variants(args.level, args.specific)


if __name__ == "__main__":
    main()