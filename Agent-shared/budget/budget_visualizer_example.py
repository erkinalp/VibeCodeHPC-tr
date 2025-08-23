#!/usr/bin/env python3
"""
予算使用履歴可視化ツール
budget_history.mdを読み取り、スパコンのポイント消費推移をグラフ化

SEエージェントがプロジェクトごとにカスタマイズして使用することを想定
配置場所: Agent-shared/budget/budget_visualizer.py
出力先: User-shared/visualizations/budget_usage.png
"""

import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import argparse

class BudgetVisualizer:
    """budget_history.mdから予算使用状況を可視化するクラス"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.budget_file = self.project_root / "Agent-shared" / "budget_history.md"
        self.output_dir = self.project_root / "User-shared" / "visualizations"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # デフォルトの閾値（プロジェクトごとにカスタマイズ）
        self.thresholds = {
            "minimum": 100,     # 最低消費ライン
            "expected": 5000,   # 想定消費ライン
            "deadline": 10000   # デッドライン
        }
        
    def parse_budget_history(self, content: str) -> List[Tuple[datetime, float]]:
        """
        budget_history.mdから時刻と使用量を抽出
        
        Returns:
            [(datetime, used_points), ...] のリスト
        """
        entries = []
        
        # UTC時刻と使用量のパターン
        time_pattern = r'UTC時刻:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)'
        used_pattern = r'本プロジェクトでの使用量:\s*([\d,]+)\s*ポイント'
        
        # セクションごとに処理
        sections = content.split('##')
        
        for section in sections:
            if not section.strip():
                continue
                
            # 時刻を探す
            time_match = re.search(time_pattern, section)
            if not time_match:
                continue
                
            timestamp = datetime.fromisoformat(time_match.group(1).replace('Z', '+00:00'))
            
            # 使用量を探す
            used_match = re.search(used_pattern, section)
            if used_match:
                # カンマを除去して数値に変換
                used_points = float(used_match.group(1).replace(',', ''))
                entries.append((timestamp, used_points))
            # プロジェクト開始時は使用量0として記録
            elif 'プロジェクト開始時' in section:
                entries.append((timestamp, 0.0))
        
        # 時刻でソート
        entries.sort(key=lambda x: x[0])
        return entries
    
    def extract_thresholds(self, content: str) -> Dict[str, float]:
        """
        budget_history.mdから予算閾値を抽出（存在する場合）
        """
        thresholds = {}
        
        # 閾値のパターン
        patterns = {
            "minimum": r'最低消費量[^:]*:\s*([\d,]+)\s*ポイント',
            "expected": r'想定消費量[^:]*:\s*([\d,]+)\s*ポイント',
            "deadline": r'デッドライン[^:]*:\s*([\d,]+)\s*ポイント'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                thresholds[key] = float(match.group(1).replace(',', ''))
        
        return thresholds if thresholds else self.thresholds
    
    def generate_graph(self, entries: List[Tuple[datetime, float]], 
                      thresholds: Dict[str, float],
                      output_path: Optional[Path] = None):
        """
        予算使用推移グラフを生成
        
        Args:
            entries: [(datetime, used_points), ...] のリスト
            thresholds: 閾値の辞書
            output_path: 出力先パス（省略時はデフォルト）
        """
        if not entries:
            print("⚠️  データが見つかりません")
            return
            
        # データを分離
        times = [entry[0] for entry in entries]
        points = [entry[1] for entry in entries]
        
        # グラフ設定
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # メインのプロット（階段状）
        ax.step(times, points, where='post', marker='o', markersize=8, 
                linewidth=2, color='#2E86AB', label='使用ポイント')
        
        # 最新値を強調
        if points:
            latest_time = times[-1]
            latest_points = points[-1]
            ax.scatter(latest_time, latest_points, s=100, color='red', 
                      zorder=5, label=f'現在: {latest_points:,.0f}')
            
            # 最新値にアノテーション
            ax.annotate(f'{latest_points:,.0f} pts', 
                       xy=(latest_time, latest_points),
                       xytext=(10, 10), textcoords='offset points',
                       fontsize=11, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', 
                                facecolor='yellow', alpha=0.7))
        
        # 閾値ライン
        if 'minimum' in thresholds:
            ax.axhline(y=thresholds['minimum'], color='green', 
                      linestyle='--', linewidth=1.5, 
                      label=f'最低消費ライン ({thresholds["minimum"]:,.0f})')
        
        if 'expected' in thresholds:
            ax.axhline(y=thresholds['expected'], color='orange', 
                      linestyle='--', linewidth=1.5, 
                      label=f'想定消費ライン ({thresholds["expected"]:,.0f})')
        
        if 'deadline' in thresholds:
            ax.axhline(y=thresholds['deadline'], color='red', 
                      linestyle='--', linewidth=2, 
                      label=f'デッドライン ({thresholds["deadline"]:,.0f})')
        
        # 消費率の計算と表示
        if points and 'deadline' in thresholds and thresholds['deadline'] > 0:
            usage_rate = (points[-1] / thresholds['deadline']) * 100
            title_suffix = f' (消費率: {usage_rate:.1f}%)'
        else:
            title_suffix = ''
        
        # グラフの装飾
        ax.set_title(f'VibeCodeHPC 予算使用推移{title_suffix}', 
                    fontsize=16, fontweight='bold')
        ax.set_xlabel('時刻', fontsize=12)
        ax.set_ylabel('使用ポイント（相対値）', fontsize=12)
        
        # X軸のフォーマット
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # グリッドと凡例
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', framealpha=0.9)
        
        # Y軸の範囲設定（0から最大閾値の1.1倍まで）
        max_threshold = max(thresholds.values()) if thresholds else max(points) if points else 1000
        ax.set_ylim(0, max_threshold * 1.1)
        
        # Y軸のフォーマット（千単位のカンマ）
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # 背景色の設定（警告レベルに応じて）
        if points and 'deadline' in thresholds:
            current = points[-1]
            if current >= thresholds['deadline']:
                ax.set_facecolor('#ffebee')  # 赤っぽい背景
            elif 'expected' in thresholds and current >= thresholds['expected']:
                ax.set_facecolor('#fff3e0')  # オレンジっぽい背景
        
        plt.tight_layout()
        
        # 保存
        if output_path is None:
            output_path = self.output_dir / "budget_usage.png"
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ グラフ生成完了: {output_path}")
        
    def generate_summary_report(self, entries: List[Tuple[datetime, float]], 
                              thresholds: Dict[str, float]):
        """
        サマリーレポートを生成
        """
        report_path = self.output_dir.parent / "reports" / "budget_summary.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 予算使用状況サマリー\n\n")
            f.write(f"生成日時: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            
            if entries:
                start_time = entries[0][0]
                latest_time = entries[-1][0]
                latest_points = entries[-1][1]
                elapsed = (latest_time - start_time).total_seconds() / 3600  # 時間単位
                
                f.write("## 現在の状況\n\n")
                f.write(f"- プロジェクト開始: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                f.write(f"- 最終確認: {latest_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                f.write(f"- 経過時間: {elapsed:.1f} 時間\n")
                f.write(f"- **現在の使用量: {latest_points:,.0f} ポイント**\n")
                
                if elapsed > 0:
                    rate = latest_points / elapsed
                    f.write(f"- 平均消費率: {rate:.1f} ポイント/時間\n")
                
                f.write("\n## 閾値との比較\n\n")
                for key, label in [("minimum", "最低消費"), 
                                  ("expected", "想定消費"), 
                                  ("deadline", "デッドライン")]:
                    if key in thresholds:
                        threshold = thresholds[key]
                        percentage = (latest_points / threshold * 100) if threshold > 0 else 0
                        status = "✅" if latest_points < threshold else "⚠️"
                        f.write(f"- {label}: {threshold:,.0f} ポイント "
                               f"({percentage:.1f}%) {status}\n")
                
                # 残り予算の推定
                if 'deadline' in thresholds and elapsed > 0:
                    remaining = thresholds['deadline'] - latest_points
                    if remaining > 0 and rate > 0:
                        hours_left = remaining / rate
                        f.write(f"\n## 推定\n\n")
                        f.write(f"- 残り予算: {remaining:,.0f} ポイント\n")
                        f.write(f"- 現在のペースでの枯渇まで: 約 {hours_left:.1f} 時間\n")
            
            f.write("\n## 可視化\n\n")
            f.write("- [予算使用推移グラフ](../visualizations/budget_usage.png)\n")
        
        print(f"✅ サマリーレポート生成: {report_path}")
    
    def run(self):
        """メイン処理を実行"""
        if not self.budget_file.exists():
            print(f"❌ budget_history.md が見つかりません: {self.budget_file}")
            return
            
        # ファイル読み込み
        with open(self.budget_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # データ解析
        entries = self.parse_budget_history(content)
        if not entries:
            print("⚠️  使用履歴データが見つかりません")
            return
            
        # 閾値の抽出（ファイルに記載があれば優先）
        thresholds = self.extract_thresholds(content)
        
        print(f"📊 {len(entries)} 件のデータポイントを検出")
        print(f"📈 閾値: 最低={thresholds.get('minimum', 'N/A')}, "
              f"想定={thresholds.get('expected', 'N/A')}, "
              f"デッドライン={thresholds.get('deadline', 'N/A')}")
        
        # グラフ生成
        self.generate_graph(entries, thresholds)
        
        # レポート生成
        self.generate_summary_report(entries, thresholds)


def main():
    """コマンドライン実行用"""
    parser = argparse.ArgumentParser(description='予算使用履歴を可視化')
    parser.add_argument('--root', type=str, default='.',
                       help='プロジェクトルートディレクトリ')
    parser.add_argument('--output', type=str, default=None,
                       help='出力ファイル名（省略時はデフォルト）')
    
    args = parser.parse_args()
    
    visualizer = BudgetVisualizer(project_root=args.root)
    
    # 出力パスの設定
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = None
    
    # 実行
    visualizer.run()


if __name__ == "__main__":
    main()