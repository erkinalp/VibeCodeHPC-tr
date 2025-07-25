#!/usr/bin/env python3
"""
OpenCodeAT コンテキスト使用率可視化スクリプト
収集したメトリクスから時系列グラフを生成
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import seaborn as sns

# 日本語フォント設定（環境に応じて調整）
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ContextVisualizer:
    """コンテキスト使用率の可視化"""
    
    def __init__(self, data_dir: Path = Path("telemetry/context_usage"),
                 output_dir: Path = Path("telemetry/visualization")):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # カラーパレット（エージェントタイプ別）
        self.color_map = {
            'PM': '#FF6B6B',     # 赤系
            'SE': '#4ECDC4',     # 青緑系
            'CI': '#45B7D1',     # 青系
            'PG': '#96CEB4',     # 緑系
            'CD': '#FECA57',     # 黄系
            'ID': '#DDA0DD',     # 紫系
        }
        
        # スタイル設定
        sns.set_style("whitegrid")
        plt.style.use('seaborn-v0_8-darkgrid')
    
    def load_all_metrics(self) -> pd.DataFrame:
        """すべてのメトリクスファイルを読み込み"""
        all_data = []
        
        # JSONファイルから読み込み
        for json_file in self.data_dir.glob("metrics_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # context_usageデータを抽出
                    for entry in data.get('context_usage', []):
                        entry['timestamp'] = pd.to_datetime(entry['timestamp'])
                        all_data.append(entry)
            except Exception as e:
                print(f"Warning: Failed to load {json_file}: {e}")
        
        # CSVファイルからも読み込み
        for csv_file in self.data_dir.glob("context_*.csv"):
            try:
                df = pd.read_csv(csv_file)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                all_data.extend(df.to_dict('records'))
            except Exception as e:
                print(f"Warning: Failed to load {csv_file}: {e}")
        
        if not all_data:
            print("No data found!")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df = df.sort_values('timestamp')
        
        # エージェントタイプを抽出（例: PG1.1.1 -> PG）
        df['agent_type'] = df['agent_id'].str.extract(r'^([A-Z]+)', expand=False)
        
        return df
    
    def plot_context_timeline(self, df: pd.DataFrame) -> Path:
        """コンテキスト使用率の時系列グラフ"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # エージェントごとにプロット
        for agent_id in df['agent_id'].unique():
            agent_data = df[df['agent_id'] == agent_id]
            agent_type = agent_data['agent_type'].iloc[0] if len(agent_data) > 0 else 'OTHER'
            color = self.color_map.get(agent_type, '#888888')
            
            ax.plot(agent_data['timestamp'], 
                   agent_data['context_percentage'],
                   label=agent_id,
                   color=color,
                   linewidth=2,
                   marker='o',
                   markersize=4,
                   alpha=0.8)
        
        # 危険ゾーンの表示
        ax.axhspan(95, 100, alpha=0.3, color='red', label='Critical Zone (95-100%)')
        ax.axhspan(80, 95, alpha=0.2, color='orange', label='Alert Zone (80-95%)')
        ax.axhspan(60, 80, alpha=0.1, color='yellow', label='Warning Zone (60-80%)')
        
        # フォーマット設定
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Context Usage (%)', fontsize=12)
        ax.set_title('Claude Code Context Usage Timeline by Agent', fontsize=16, fontweight='bold')
        
        # X軸の日時フォーマット
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.xticks(rotation=45)
        
        # 凡例
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        
        # グリッド
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
        
        # レイアウト調整
        plt.tight_layout()
        
        # 保存
        output_file = self.output_dir / f"context_usage_timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def plot_agent_comparison(self, df: pd.DataFrame) -> Path:
        """エージェント別の最大コンテキスト使用率比較"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # エージェントごとの最大使用率を計算
        max_usage = df.groupby('agent_id').agg({
            'context_percentage': 'max',
            'agent_type': 'first'
        }).reset_index()
        
        # ソート
        max_usage = max_usage.sort_values('context_percentage', ascending=True)
        
        # 色の設定
        colors = [self.color_map.get(agent_type, '#888888') 
                 for agent_type in max_usage['agent_type']]
        
        # 横棒グラフ
        bars = ax.barh(max_usage['agent_id'], 
                       max_usage['context_percentage'],
                       color=colors,
                       alpha=0.8,
                       edgecolor='black',
                       linewidth=1)
        
        # 値をバーの端に表示
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                   f'{width:.1f}%',
                   ha='left', va='center', fontsize=10)
        
        # 危険ラインの表示
        ax.axvline(x=95, color='red', linestyle='--', alpha=0.7, label='Critical Threshold')
        ax.axvline(x=80, color='orange', linestyle='--', alpha=0.5, label='Alert Threshold')
        ax.axvline(x=60, color='yellow', linestyle='--', alpha=0.3, label='Warning Threshold')
        
        # フォーマット設定
        ax.set_xlabel('Maximum Context Usage (%)', fontsize=12)
        ax.set_ylabel('Agent ID', fontsize=12)
        ax.set_title('Maximum Context Usage by Agent', fontsize=16, fontweight='bold')
        ax.set_xlim(0, 105)
        
        # 凡例
        ax.legend(loc='lower right')
        
        # グリッド
        ax.grid(True, axis='x', alpha=0.3)
        
        # レイアウト調整
        plt.tight_layout()
        
        # 保存
        output_file = self.output_dir / f"agent_max_context_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def plot_token_distribution(self, df: pd.DataFrame) -> Path:
        """トークン使用量の分布"""
        # トークン使用量データを集計
        token_data = []
        
        # すべてのJSONファイルから token_usage を収集
        for json_file in self.data_dir.glob("metrics_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry in data.get('token_usage', []):
                        if entry['token_type'] in ['input', 'output']:
                            token_data.append({
                                'agent_id': entry['agent_id'],
                                'token_type': entry['token_type'],
                                'value': entry['value']
                            })
            except:
                continue
        
        if not token_data:
            print("No token data found for distribution plot")
            return None
        
        token_df = pd.DataFrame(token_data)
        
        # エージェントタイプを抽出
        token_df['agent_type'] = token_df['agent_id'].str.extract(r'^([A-Z]+)', expand=False)
        
        # 集計
        summary = token_df.groupby(['agent_id', 'agent_type', 'token_type'])['value'].sum().unstack(fill_value=0)
        summary['total'] = summary.get('input', 0) + summary.get('output', 0)
        summary = summary.sort_values('total', ascending=True)
        
        # プロット
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # スタック横棒グラフ
        y_pos = range(len(summary))
        
        # Input tokens
        bars1 = ax.barh(y_pos, summary.get('input', 0), 
                        label='Input Tokens',
                        color='#3498db',
                        alpha=0.8)
        
        # Output tokens
        bars2 = ax.barh(y_pos, summary.get('output', 0), 
                        left=summary.get('input', 0),
                        label='Output Tokens',
                        color='#e74c3c',
                        alpha=0.8)
        
        # 設定
        ax.set_yticks(y_pos)
        ax.set_yticklabels(summary.index.get_level_values('agent_id'))
        ax.set_xlabel('Total Tokens', fontsize=12)
        ax.set_ylabel('Agent ID', fontsize=12)
        ax.set_title('Token Usage Distribution by Agent', fontsize=16, fontweight='bold')
        
        # 凡例
        ax.legend(loc='lower right')
        
        # グリッド
        ax.grid(True, axis='x', alpha=0.3)
        
        # レイアウト調整
        plt.tight_layout()
        
        # 保存
        output_file = self.output_dir / f"token_distribution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def generate_summary_report(self, df: pd.DataFrame) -> Path:
        """サマリーレポートの生成"""
        report_file = self.output_dir / f"context_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# OpenCodeAT Context Usage Summary Report\n\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            
            # 全体統計
            f.write("## Overall Statistics\n\n")
            f.write(f"- Total data points: {len(df)}\n")
            f.write(f"- Monitoring period: {df['timestamp'].min()} to {df['timestamp'].max()}\n")
            f.write(f"- Number of agents: {df['agent_id'].nunique()}\n\n")
            
            # エージェント別統計
            f.write("## Agent Statistics\n\n")
            f.write("| Agent ID | Type | Max Context % | Avg Context % | Last Context % | Data Points |\n")
            f.write("|----------|------|---------------|---------------|----------------|-------------|\n")
            
            for agent_id in sorted(df['agent_id'].unique()):
                agent_data = df[df['agent_id'] == agent_id]
                agent_type = agent_data['agent_type'].iloc[0]
                max_context = agent_data['context_percentage'].max()
                avg_context = agent_data['context_percentage'].mean()
                last_context = agent_data['context_percentage'].iloc[-1]
                data_points = len(agent_data)
                
                # 危険度に応じて強調
                if max_context > 95:
                    agent_id = f"**{agent_id}**"
                    status = " 🚨"
                elif max_context > 80:
                    agent_id = f"**{agent_id}**"
                    status = " ⚠️"
                elif max_context > 60:
                    status = " ⚡"
                else:
                    status = ""
                
                f.write(f"| {agent_id}{status} | {agent_type} | {max_context:.1f}% | "
                       f"{avg_context:.1f}% | {last_context:.1f}% | {data_points} |\n")
            
            # 警告事項
            critical_usage = df[df['context_percentage'] > 95]['agent_id'].unique()
            high_usage = df[(df['context_percentage'] > 80) & (df['context_percentage'] <= 95)]['agent_id'].unique()
            
            if len(critical_usage) > 0:
                f.write("\n## 🚨 Critical Context Usage (>95%)\n\n")
                f.write("These agents need immediate attention:\n")
                for agent in critical_usage:
                    max_usage = df[df['agent_id'] == agent]['context_percentage'].max()
                    f.write(f"- **{agent}: {max_usage:.1f}%** - Auto-compact imminent\n")
            
            if len(high_usage) > 0:
                f.write("\n## ⚠️ High Context Usage (80-95%)\n\n")
                f.write("These agents are approaching critical levels:\n")
                for agent in high_usage:
                    max_usage = df[df['agent_id'] == agent]['context_percentage'].max()
                    f.write(f"- {agent}: {max_usage:.1f}%\n")
            
            f.write("\n## Visualization Files\n\n")
            f.write("- Context usage timeline: `context_usage_timeline_*.png`\n")
            f.write("- Agent comparison: `agent_max_context_*.png`\n")
            f.write("- Token distribution: `token_distribution_*.png`\n")
        
        return report_file


def main():
    """メイン処理"""
    visualizer = ContextVisualizer()
    
    print("Loading metrics data...")
    df = visualizer.load_all_metrics()
    
    if df.empty:
        print("No data available for visualization.")
        return
    
    print(f"Loaded {len(df)} data points from {df['agent_id'].nunique()} agents")
    
    # 可視化の生成
    print("\nGenerating visualizations...")
    
    # 1. 時系列グラフ
    timeline_file = visualizer.plot_context_timeline(df)
    print(f"✓ Context timeline saved to: {timeline_file}")
    
    # 2. エージェント比較
    comparison_file = visualizer.plot_agent_comparison(df)
    print(f"✓ Agent comparison saved to: {comparison_file}")
    
    # 3. トークン分布
    token_file = visualizer.plot_token_distribution(df)
    if token_file:
        print(f"✓ Token distribution saved to: {token_file}")
    
    # 4. サマリーレポート
    report_file = visualizer.generate_summary_report(df)
    print(f"✓ Summary report saved to: {report_file}")
    
    print("\n✅ Visualization complete!")


if __name__ == "__main__":
    main()