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
            'local': {},     # PGごと（相対パスベース）
            'family': {},    # 親子関係（第1世代→第2世代）
            'hardware': {},  # ハードウェア構成ごと
            'project': []    # プロジェクト全体
        }
        
        # 世代別の技術を格納
        generation_techs = {
            1: [],  # 第1世代（単一技術）
            2: [],  # 第2世代（融合）
            3: []   # 第3世代（さらなる融合）
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
            
            # 相対作業ディレクトリを識別子とする（Flow/TypeII/を除く）
            work_dir_parts = []
            skip_parts = ['Flow', 'TypeII', 'ChangeLog.md']
            for part in parts:
                if part not in skip_parts:
                    work_dir_parts.append(part)
            
            # Local SOTA（相対パスベース）
            if work_dir_parts:
                local_id = '-'.join(work_dir_parts[:-1] + [work_dir_parts[-1].replace('_', '-')])
                if local_id not in sota_data['local']:
                    sota_data['local'][local_id] = []
                sota_data['local'][local_id].extend(entries)
            
            # 技術名を抽出（最後のディレクトリ名）
            tech_name = changelog_path.parent.name
            
            # 世代を判定（_の数で判定）
            if '_' not in tech_name:
                # 第1世代（単一技術、深化含む）
                generation = 1
                generation_techs[1].append((tech_name, entries))
            elif tech_name.count('_') == 1:
                # 第2世代（2つの技術の融合）
                generation = 2
                generation_techs[2].append((tech_name, entries))
            else:
                # 第3世代以降
                generation = 3
                generation_techs[3].append((tech_name, entries))
            
            # Hardware SOTA（hardware_info.mdの位置で階層を判定）
            hardware_path = None
            for i in range(len(parts)):
                check_path = self.project_root / Path(*parts[:i+1])
                if (check_path / 'hardware_info.md').exists():
                    hardware_path = '/'.join(parts[:i+1])
                    break
            
            if hardware_path:
                if hardware_path not in sota_data['hardware']:
                    sota_data['hardware'][hardware_path] = []
                sota_data['hardware'][hardware_path].extend(entries)
            
            # Project SOTA（全エントリ）
            sota_data['project'].extend(entries)
        
        # Family SOTAを構築（親子関係）
        # 第2世代の各技術について、その親となる第1世代を見つける
        for gen2_tech, gen2_entries in generation_techs[2]:
            parent_techs = gen2_tech.split('_')
            family_name = f"Family:{gen2_tech}"
            sota_data['family'][family_name] = {
                'child': gen2_entries,
                'parents': {}
            }
            
            # 親技術のデータを収集
            for parent_tech in parent_techs:
                for gen1_tech, gen1_entries in generation_techs[1]:
                    # 完全一致で親技術を探す
                    if gen1_tech == parent_tech:
                        sota_data['family'][family_name]['parents'][parent_tech] = gen1_entries
                        break
        
        return sota_data
    
    def extract_sota_progression(self, entries: List[Dict]) -> Tuple[List, List, List]:
        """エントリからSOTA更新の推移を抽出（全生成での位置を保持）"""
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
        for i, entry in enumerate(sorted_entries):
            if entry['value'] > max_value:  # SOTA更新時のみ記録
                max_value = entry['value']
                values.append(entry['value'])
                versions.append(entry['version'])
                
                if self.x_axis_type == 'time' and entry['timestamp']:
                    if not start_time:
                        start_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    current_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    elapsed_seconds = (current_time - start_time).total_seconds()
                    times.append(elapsed_seconds)
                else:
                    # カウントベース（全生成での実際の位置を使用）
                    times.append(i)
        
        return times, values, versions
    
    def extract_all_progression(self, entries: List[Dict]) -> Tuple[List, List, List]:
        """全エントリの推移を抽出（SOTAでないものも含む）"""
        if not entries:
            return [], [], []
        
        # タイムスタンプでソート
        sorted_entries = sorted(entries, key=lambda x: x['timestamp'] or '0')
        
        # 最初のタイムスタンプからの経過時間を計算
        start_time = None
        times = []
        values = []
        versions = []
        
        for i, entry in enumerate(sorted_entries):
            values.append(entry['value'])
            versions.append(entry['version'])
            
            if self.x_axis_type == 'time' and entry['timestamp']:
                if not start_time:
                    start_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                current_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                elapsed_seconds = (current_time - start_time).total_seconds()
                times.append(elapsed_seconds)
            else:
                # カウントベース（生成順）
                times.append(i)
        
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
                            theoretical_ratio: float = 0.1,
                            specific_key: Optional[str] = None):
        """SOTA推移グラフを生成
        
        Args:
            sota_level: 'local', 'family', 'hardware', 'project'のいずれか
            x_axis: 'time'（経過時間）または 'count'（更新回数）
            log_scale: Y軸を対数スケールにするか
            show_theoretical: 理論性能を表示するか
            theoretical_ratio: 理論性能が不明な場合の上限設定（最高性能の何倍か）
            specific_key: 特定のキーのみをプロット（family/hardwareで使用）
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
            if x_axis == 'count':
                # カウントベースは全生成＋SOTA水準線
                all_times, all_values, all_versions = self.extract_all_progression(sota_data['project'])
                sota_times, sota_values, sota_versions = self.extract_sota_progression(sota_data['project'])
                
                if all_times and all_values:
                    # 全生成の折れ線
                    ax.plot(all_times, all_values, marker='o', 
                           label='All Generations', color='C0', linewidth=2.5, markersize=6, alpha=1.0, markeredgewidth=1.2)
                    
                    # 各SOTA更新点から最後まで水平線を引く（階段状になる）
                    if sota_times and sota_values and len(all_times) > 0:
                        max_time = max(all_times)
                        for i, (t, v) in enumerate(zip(sota_times, sota_values)):
                            # 各SOTA点から最後まで水平線（色指定なしでデフォルト色）
                            ax.hlines(v, t, max_time, linestyles='--', 
                                     linewidth=2.0, alpha=0.6,
                                     label='SOTA Level' if i == 0 else "")
            else:
                # 時間ベースはSOTAのみ
                times, values, versions = self.extract_sota_progression(sota_data['project'])
                if times and values:
                    ax.step(times, values, where='post', marker='o', 
                           label='SOTA Performance', color='C0', linewidth=3.0, markersize=7, markeredgewidth=1.5)
                
                # 理論性能の表示
                if show_theoretical and values:
                    max_value = max(values)
                    theoretical = self.theoretical_perf or (max_value * (1 + theoretical_ratio))
                    ax.axhline(y=theoretical, color='red', linestyle='--', 
                             label=f'Theoretical Peak ({theoretical:.1f} GFLOPS)')
        
        elif sota_level == 'family':
            # Family階層（親子関係）
            data_dict = sota_data['family']
            
            # 特定のファミリーのみをプロット
            if specific_key:
                data_dict = {specific_key: data_dict[specific_key]} if specific_key in data_dict else {}
            
            # 色の設定（論文向けの標準的な原色を使用）
            # matplotlibのデフォルトカラーサイクル（C0, C1, C2...）を使用
            parent_colors = {'OpenMP': 'C0', 'MPI': 'C1', 'CUDA': 'C2', 'AVX2': 'C3'}
            child_colors = {'OpenMP_MPI': 'C4', 'OpenMP_CUDA': 'C5', 'MPI_CUDA': 'C6', 'OpenMP_AVX2': 'C7'}
            
            for family_name, family_data in data_dict.items():
                if isinstance(family_data, dict) and 'child' in family_data:
                    if x_axis == 'count':
                        # カウントベースは全生成＋SOTA水準線
                        # 子（第2世代）
                        child_name = family_name.replace('Family:', '')
                        all_times, all_values, all_versions = self.extract_all_progression(family_data['child'])
                        sota_times, sota_values, sota_versions = self.extract_sota_progression(family_data['child'])
                        
                        if all_times and all_values:
                            color = child_colors.get(child_name, 'navy')
                            # 全生成の折れ線（太く濃く表示）
                            ax.plot(all_times, all_values, marker='o',
                                   label=f'{child_name} (Gen2)',
                                   color=color, linewidth=3.0, markersize=8, alpha=1.0, markeredgewidth=1.5)
                            
                            # 各SOTA更新点から最後まで水平線
                            if sota_times and sota_values and len(all_times) > 0:
                                max_time = max(all_times)
                                for j, (t, v) in enumerate(zip(sota_times, sota_values)):
                                    ax.hlines(v, t, max_time, colors=color, linestyles='--',
                                             linewidth=2.5, alpha=0.8)
                        
                        # 親（第1世代）
                        for parent_name, parent_entries in family_data.get('parents', {}).items():
                            all_times, all_values, all_versions = self.extract_all_progression(parent_entries)
                            sota_times, sota_values, sota_versions = self.extract_sota_progression(parent_entries)
                            
                            if all_times and all_values:
                                color = parent_colors.get(parent_name, 'darkgray')
                                ax.plot(all_times, all_values, marker='^',
                                       label=f'{parent_name} (Gen1)',
                                       color=color, linewidth=2.5, markersize=6, alpha=1.0, linestyle=':')
                                
                                # 各SOTA更新点から最後まで水平線
                                if sota_times and sota_values and len(all_times) > 0:
                                    max_time = max(all_times)
                                    for j, (t, v) in enumerate(zip(sota_times, sota_values)):
                                        ax.hlines(v, t, max_time, colors=color, linestyles=':',
                                                 linewidth=2.0, alpha=0.7)
                    else:
                        # 時間ベースはSOTAのみ階段状
                        # 子（第2世代）
                        child_name = family_name.replace('Family:', '')
                        times, values, versions = self.extract_sota_progression(family_data['child'])
                        if times and values:
                            color = child_colors.get(child_name, 'navy')
                            ax.step(times, values, where='post', marker='o',
                                   label=f'{child_name} (Gen2, Max: {max(values):.1f})',
                                   color=color, linewidth=2.5, markersize=7, markeredgewidth=1.5)
                        
                        # 親（第1世代）
                        for parent_name, parent_entries in family_data.get('parents', {}).items():
                            times, values, versions = self.extract_sota_progression(parent_entries)
                            if times and values:
                                color = parent_colors.get(parent_name, 'darkgray')
                                ax.step(times, values, where='post', marker='s',
                                       label=f'{parent_name} (Gen1, Max: {max(values):.1f})',
                                       color=color, linewidth=2.0, markersize=5, alpha=0.9, linestyle='--')
        
        elif sota_level in ['local', 'hardware']:
            # 複数のグラフ
            data_dict = sota_data[sota_level]
            
            # hardwareレベルでspecific_keyが指定された場合の処理
            if sota_level == 'hardware' and specific_key:
                filtered_dict = {}
                for key, entries in data_dict.items():
                    # hw_keyの最後の部分でフィルタリング
                    path_parts = key.split('/')
                    if path_parts and path_parts[-1] == specific_key:
                        filtered_dict[key] = entries
                data_dict = filtered_dict
            # 特定のキーのみをプロット（その他の場合）
            elif specific_key:
                data_dict = {specific_key: data_dict[specific_key]} if specific_key in data_dict else {}
            
            # matplotlibのデフォルトカラーサイクルを使用（論文向けの濃い原色）
            # C0=青, C1=オレンジ, C2=緑, C3=赤, C4=紫, C5=茶, C6=ピンク, C7=灰, C8=黄緑, C9=水色
            colors = [f'C{i}' for i in range(min(10, len(data_dict)))]
            
            for i, (key, entries) in enumerate(data_dict.items()):
                if x_axis == 'count':
                    # カウントベースは全生成＋SOTA水準線
                    all_times, all_values, all_versions = self.extract_all_progression(entries)
                    sota_times, sota_values, sota_versions = self.extract_sota_progression(entries)
                    
                    if all_times and all_values:
                        color = colors[i % len(colors)]
                        # 全生成の折れ線
                        ax.plot(all_times, all_values, marker='o',
                               label=f'{key}',
                               color=color, linewidth=2.5, markersize=6, alpha=1.0, markeredgewidth=1.2)
                        
                        # 各SOTA更新点から最後まで水平線
                        if sota_times and sota_values and len(all_times) > 0:
                            max_time = max(all_times)
                            for j, (t, v) in enumerate(zip(sota_times, sota_values)):
                                ax.hlines(v, t, max_time, colors=color, linestyles='--',
                                         linewidth=2.0, alpha=0.7)
                else:
                    # 時間ベースはSOTAのみ階段状
                    times, values, versions = self.extract_sota_progression(entries)
                    if times and values:
                        color = colors[i % len(colors)]
                        ax.step(times, values, where='post', marker='o',
                               label=f'{key} (Max: {max(values):.1f})',
                               color=color, linewidth=2.5, markersize=6, markeredgewidth=1.2)
        
        # 軸設定
        if x_axis == 'time':
            ax.set_xlabel('Time (seconds from start)')
            # 秒を分に変換して表示（読みやすさのため）
            import matplotlib.ticker as ticker
            def format_seconds(x, pos):
                minutes = int(x // 60)
                seconds = int(x % 60)
                if x < 60:
                    return f'{int(x)}s'
                elif seconds == 0:
                    return f'{minutes}m'
                else:
                    return f'{minutes}m{seconds}s'
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_seconds))
        else:
            ax.set_xlabel('Code Generation Count')
            # X軸を整数表示にする
            import matplotlib.ticker as ticker
            ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        
        ax.set_ylabel('Performance (GFLOPS equivalent)')
        
        if log_scale:
            ax.set_yscale('log')
        
        # 右y軸にも目盛りを表示
        ax2 = ax.twinx()
        ax2.set_ylim(ax.get_ylim())
        if log_scale:
            ax2.set_yscale('log')  # 右軸も対数スケールに設定
        ax2.set_ylabel('')  # 右側にはラベルなし
        ax2.tick_params(axis='y', which='both', length=5)
        
        # グラフ装飾
        ax.set_title(f'SOTA Performance Progression - {sota_level.capitalize()} Level')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # ファイル保存（階層別ディレクトリに）
        if x_axis == 'count':
            filename = f"generation_{sota_level}_{x_axis}"
        else:
            filename = f"sota_{sota_level}_{x_axis}"
        
        if log_scale:
            filename += "_log"
        
        # 適切な出力ディレクトリを選択
        if sota_level in self.output_dirs:
            output_dir = self.output_dirs[sota_level]
        else:
            output_dir = self.base_output_dir
        
        # specific_keyがある場合はサブディレクトリに保存
        if specific_key:
            # ファイル名として使える形式に変換
            safe_key = specific_key.replace('Family:', '').replace('/', '_').replace(':', '_')
            # サブディレクトリを作成
            output_dir = output_dir / safe_key
            output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{filename}.png"
        
        plt.savefig(output_path, dpi=120, bbox_inches='tight')
        plt.close()
        
        print(f"✅ SOTA graph saved: {output_path}")
        return output_path
    
    def generate_all_graphs(self):
        """全パターンのグラフを生成"""
        generated_files = []  # 生成されたファイルパスを記録
        
        # プロジェクトレベル（1つのグラフ）
        for x_axis in ['time', 'count']:
            for log_scale in [False, True]:
                if x_axis == 'count' and log_scale:
                    continue  # カウント軸の対数は不要
                path = self.plot_sota_comparison('project', x_axis, log_scale, True)
                generated_files.append(path)
        
        # ローカルレベル（1つのグラフに全PG）
        for x_axis in ['time', 'count']:
            for log_scale in [False, True]:
                if x_axis == 'count' and log_scale:
                    continue
                path = self.plot_sota_comparison('local', x_axis, log_scale, True)
                generated_files.append(path)
        
        # ファミリーレベル（各ファミリーごとに個別グラフ）
        sota_data = self.collect_sota_data()
        for family_key in sota_data['family'].keys():
            for x_axis in ['time', 'count']:
                for log_scale in [False, True]:
                    if x_axis == 'count' and log_scale:
                        continue
                    path = self.plot_sota_comparison('family', x_axis, log_scale, True, specific_key=family_key)
                    generated_files.append(path)
        
        # ハードウェアレベル（hardware_info.mdの親ディレクトリ名でグループ化）
        hardware_groups = {}
        for hw_key in sota_data['hardware'].keys():
            # hw_keyの最後の部分をグループ名とする
            # 例: Flow/TypeII/single-node → single-node
            # 例: Flow/TypeII/multi-gpu → multi-gpu
            path_parts = hw_key.split('/')
            if path_parts:
                hw_group = path_parts[-1]  # 最後の要素をグループ名に
                if hw_group not in hardware_groups:
                    hardware_groups[hw_group] = []
                hardware_groups[hw_group].append(hw_key)
        
        # 各ハードウェアグループごとにグラフ生成
        for hw_group in hardware_groups.keys():
            for x_axis in ['time', 'count']:
                for log_scale in [False, True]:
                    if x_axis == 'count' and log_scale:
                        continue
                    path = self.plot_sota_comparison('hardware', x_axis, log_scale, True, 
                                                    specific_key=hw_group)
                    generated_files.append(path)
        
        # レポート生成
        self.generate_visualization_report(len(generated_files))
        
        print(f"✅ All SOTA graphs generated: {len(generated_files)} files")
        return generated_files
    
    def generate_all_graphs_with_milestone(self, elapsed_minutes: int = 0):
        """マイルストーン付きで全グラフ生成
        
        Args:
            elapsed_minutes: プロジェクト開始からの経過時間（分）
        """
        # マイルストーン判定
        milestones = [30, 60, 90, 120, 180]
        is_milestone = elapsed_minutes in milestones
        
        # 通常のグラフ生成
        generated_files = self.generate_all_graphs()
        
        # マイルストーン時はコピーを保存
        if is_milestone:
            milestone_dir = self.base_output_dir / 'milestones' / f'{elapsed_minutes}min'
            milestone_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in generated_files:
                if Path(file_path).exists():
                    import shutil
                    dest = milestone_dir / Path(file_path).name
                    shutil.copy2(file_path, dest)
            
            print(f"✅ Milestone graphs saved: {milestone_dir}")
        
        return generated_files
    
    def generate_visualization_report(self, total_count: int):
        """可視化レポートを自動生成"""
        report_dir = self.project_root / "User-shared" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "sota_visualization_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# SOTA Visualization Report\n\n")
            f.write(f"Generated: {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n")
            
            # プロジェクトレベル
            project_dir = self.output_dirs['project']
            if project_dir.exists():
                f.write(f"## Project Level\n\n")
                for file_name in ['generation_project_count', 'sota_project_time', 'sota_project_time_log']:
                    png_file = project_dir / f"{file_name}.png"
                    if png_file.exists():
                        rel_path = Path("../visualizations/sota/project") / png_file.name
                        f.write(f"### {png_file.stem}\n")
                        f.write(f"![{png_file.stem}]({rel_path})\n\n")
            
            # ハードウェアレベル
            hardware_dir = self.output_dirs['hardware']
            if hardware_dir.exists():
                f.write(f"## Hardware Level\n\n")
                for file_name in ['generation_hardware_count', 'sota_hardware_time', 'sota_hardware_time_log']:
                    png_file = hardware_dir / f"{file_name}.png"
                    if png_file.exists():
                        rel_path = Path("../visualizations/sota/hardware") / png_file.name
                        f.write(f"### {png_file.stem}\n")
                        f.write(f"![{png_file.stem}]({rel_path})\n\n")
            
            # ファミリーレベル
            family_dir = self.output_dirs['family']
            if family_dir.exists():
                f.write(f"## Family Level\n\n")
                for file_name in ['generation_family_count', 'sota_family_time', 'sota_family_time_log']:
                    png_file = family_dir / f"{file_name}.png"
                    if png_file.exists():
                        rel_path = Path("../visualizations/sota/family") / png_file.name
                        f.write(f"### {png_file.stem}\n")
                        f.write(f"![{png_file.stem}]({rel_path})\n\n")
            
            # ローカルレベル
            local_dir = self.output_dirs['local']
            if local_dir.exists():
                f.write(f"## Local Level\n\n")
                for file_name in ['generation_local_count', 'sota_local_time', 'sota_local_time_log']:
                    png_file = local_dir / f"{file_name}.png"
                    if png_file.exists():
                        rel_path = Path("../visualizations/sota/local") / png_file.name
                        f.write(f"### {png_file.stem}\n")
                        f.write(f"![{png_file.stem}]({rel_path})\n\n")
            
            f.write(f"\n## Summary\n")
            f.write(f"- Total graphs: 12\n")  # 各レベル3つずつ×4レベル
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