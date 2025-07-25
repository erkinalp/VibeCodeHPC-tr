#!/usr/bin/env python3
"""
OpenCodeAT テレメトリ収集スクリプト
Claude CodeのOpenTelemetryコンソール出力を解析し、構造化データとして保存
"""

import re
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class MetricsCollector:
    """コンソール出力からメトリクスを収集"""
    
    def __init__(self, output_dir: Path = Path("telemetry/context_usage")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # メトリクスパターンの定義
        self.patterns = {
            'token_usage': re.compile(
                r'claude_code\.token\.usage{.*?type="(input|output|cacheRead|cacheCreation)".*?agent_id="([^"]+)".*?} (\d+)'
            ),
            'session_id': re.compile(
                r'session\.id="([^"]+)"'
            ),
            'api_request': re.compile(
                r'event\.name="api_request".*?input_tokens=(\d+).*?output_tokens=(\d+).*?model="([^"]+)"'
            ),
            'timestamp': re.compile(
                r'timestamp="([^"]+)"'
            )
        }
        
        self.metrics_data = {
            'sessions': {},  # session_id -> agent_id マッピング
            'token_usage': [],  # トークン使用履歴
            'api_requests': [],  # APIリクエスト履歴
            'context_usage': []  # コンテキスト使用率履歴
        }
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """1行を解析してメトリクスを抽出"""
        
        # トークン使用量の抽出
        token_match = self.patterns['token_usage'].search(line)
        if token_match:
            token_type, agent_id, value = token_match.groups()
            
            # セッションIDの抽出
            session_match = self.patterns['session_id'].search(line)
            session_id = session_match.group(1) if session_match else "unknown"
            
            # タイムスタンプの抽出（なければ現在時刻）
            timestamp_match = self.patterns['timestamp'].search(line)
            timestamp = timestamp_match.group(1) if timestamp_match else datetime.utcnow().isoformat()
            
            metric = {
                'timestamp': timestamp,
                'agent_id': agent_id,
                'session_id': session_id,
                'token_type': token_type,
                'value': int(value),
                'metric_type': 'token_usage'
            }
            
            self.metrics_data['token_usage'].append(metric)
            self.metrics_data['sessions'][session_id] = agent_id
            
            # inputトークンの場合、コンテキスト使用率を計算
            if token_type == 'input':
                context_usage = {
                    'timestamp': timestamp,
                    'agent_id': agent_id,
                    'session_id': session_id,
                    'tokens_used': int(value),
                    'context_percentage': (int(value) / 200000) * 100,
                    'metric_type': 'context_usage'
                }
                self.metrics_data['context_usage'].append(context_usage)
            
            return metric
        
        # APIリクエストイベントの抽出
        api_match = self.patterns['api_request'].search(line)
        if api_match:
            input_tokens, output_tokens, model = api_match.groups()
            
            timestamp_match = self.patterns['timestamp'].search(line)
            timestamp = timestamp_match.group(1) if timestamp_match else datetime.utcnow().isoformat()
            
            # エージェントIDの抽出
            agent_match = re.search(r'agent_id="([^"]+)"', line)
            agent_id = agent_match.group(1) if agent_match else "unknown"
            
            api_metric = {
                'timestamp': timestamp,
                'agent_id': agent_id,
                'input_tokens': int(input_tokens),
                'output_tokens': int(output_tokens),
                'model': model,
                'metric_type': 'api_request'
            }
            
            self.metrics_data['api_requests'].append(api_metric)
            return api_metric
        
        return None
    
    def process_file(self, file_path: Path) -> Dict:
        """ファイル全体を処理"""
        metrics_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                metric = self.parse_line(line)
                if metric:
                    metrics_count += 1
        
        return {
            'file': str(file_path),
            'metrics_collected': metrics_count,
            'summary': self.get_summary()
        }
    
    def get_summary(self) -> Dict:
        """収集したメトリクスのサマリー"""
        summary = {
            'total_sessions': len(self.metrics_data['sessions']),
            'total_token_metrics': len(self.metrics_data['token_usage']),
            'total_api_requests': len(self.metrics_data['api_requests']),
            'agents': {}
        }
        
        # エージェント別の集計
        for agent_id in set(m['agent_id'] for m in self.metrics_data['token_usage']):
            agent_metrics = [m for m in self.metrics_data['token_usage'] if m['agent_id'] == agent_id]
            
            input_tokens = sum(m['value'] for m in agent_metrics if m['token_type'] == 'input')
            output_tokens = sum(m['value'] for m in agent_metrics if m['token_type'] == 'output')
            
            # 最新のコンテキスト使用率
            agent_context = [c for c in self.metrics_data['context_usage'] if c['agent_id'] == agent_id]
            latest_context = agent_context[-1]['context_percentage'] if agent_context else 0
            
            summary['agents'][agent_id] = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'context_usage_percentage': latest_context,
                'metric_count': len(agent_metrics)
            }
        
        return summary
    
    def save_metrics(self, agent_id: str) -> Path:
        """メトリクスをJSON形式で保存"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f"metrics_{agent_id}_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics_data, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def save_context_usage_csv(self, agent_id: str) -> Path:
        """コンテキスト使用率をCSV形式で保存（可視化用）"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        csv_file = self.output_dir / f"context_{agent_id}_{timestamp}.csv"
        
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("timestamp,agent_id,session_id,tokens_used,context_percentage\n")
            
            for entry in self.metrics_data['context_usage']:
                f.write(f"{entry['timestamp']},{entry['agent_id']},{entry['session_id']},"
                       f"{entry['tokens_used']},{entry['context_percentage']:.2f}\n")
        
        return csv_file


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python collect_metrics.py <input_file> [agent_id]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    agent_id = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    
    if not input_file.exists():
        print(f"Error: File {input_file} not found")
        sys.exit(1)
    
    collector = MetricsCollector()
    
    print(f"Processing metrics from: {input_file}")
    result = collector.process_file(input_file)
    
    print("\n📊 Metrics Summary:")
    print(f"Total metrics collected: {result['metrics_collected']}")
    
    summary = result['summary']
    print(f"\nSessions: {summary['total_sessions']}")
    print(f"Token metrics: {summary['total_token_metrics']}")
    print(f"API requests: {summary['total_api_requests']}")
    
    print("\n👤 Agent Summary:")
    for agent, stats in summary['agents'].items():
        print(f"\nAgent: {agent}")
        print(f"  Input tokens: {stats['input_tokens']:,}")
        print(f"  Output tokens: {stats['output_tokens']:,}")
        print(f"  Total tokens: {stats['total_tokens']:,}")
        print(f"  Context usage: {stats['context_usage_percentage']:.2f}%")
    
    # メトリクスを保存
    json_file = collector.save_metrics(agent_id)
    csv_file = collector.save_context_usage_csv(agent_id)
    
    print(f"\n💾 Saved metrics to:")
    print(f"  JSON: {json_file}")
    print(f"  CSV: {csv_file}")


if __name__ == "__main__":
    main()