#!/usr/bin/env python3
"""
エージェント健全性監視スクリプト
SEエージェントが定期的に実行し、異常を検知・対応する
"""

import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

class AgentMonitor:
    """エージェントの健全性を監視"""
    
    def __init__(self, project_root: Path = Path("."), 
                 se_agent_id: str = "SE1"):
        self.project_root = project_root
        self.se_agent_id = se_agent_id
        self.telemetry_dir = project_root / "telemetry"
        self.auto_compact_log = self.telemetry_dir / "auto_compact" / "auto_compact.log"
        self.context_usage_dir = self.telemetry_dir / "context_usage"
        self.monitoring_state_file = self.telemetry_dir / "monitoring_state.json"
        
        # 監視状態の読み込み
        self.state = self.load_state()
        
        # 監視閾値
        self.CONTEXT_WARNING_THRESHOLD = 95.0  # 95%で特別監視
        self.INACTIVITY_THRESHOLD = timedelta(minutes=30)
        self.RESPONSE_WAIT_TIME = timedelta(minutes=5)
    
    def load_state(self) -> Dict:
        """前回の監視状態を読み込み"""
        if self.monitoring_state_file.exists():
            with open(self.monitoring_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_auto_compact_check": {},
            "inactive_agents": {},
            "warned_agents": {}
        }
    
    def save_state(self):
        """監視状態を保存"""
        self.monitoring_state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.monitoring_state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def get_latest_context_usage(self) -> Dict[str, float]:
        """各エージェントの最新コンテキスト使用率を取得"""
        context_usage = {}
        
        # 最新のメトリクスファイルから読み込み
        for metrics_file in self.context_usage_dir.glob("metrics_*.json"):
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # context_usageから最新の値を取得
                    for entry in data.get('context_usage', []):
                        agent_id = entry['agent_id']
                        percentage = entry['context_percentage']
                        
                        # より新しいデータで更新
                        if agent_id not in context_usage or percentage > context_usage[agent_id]:
                            context_usage[agent_id] = percentage
            except Exception as e:
                print(f"Warning: Failed to read {metrics_file}: {e}")
        
        return context_usage
    
    def check_auto_compact_events(self) -> List[Dict]:
        """新しいauto-compactイベントを検出"""
        new_events = []
        
        if not self.auto_compact_log.exists():
            return new_events
        
        try:
            with open(self.auto_compact_log, 'r', encoding='utf-8') as f:
                for line in f:
                    # [AUTO-COMPACT] agent_id=PG1.1.1 timestamp=2025-07-16T12:34:56Z
                    match = re.search(r'\[AUTO-COMPACT\] agent_id=(\S+) timestamp=(\S+)', line)
                    if match:
                        agent_id = match.group(1)
                        timestamp = match.group(2)
                        
                        # 前回チェック以降の新しいイベントかどうか
                        last_check = self.state["last_auto_compact_check"].get(agent_id, "")
                        if timestamp > last_check:
                            new_events.append({
                                "agent_id": agent_id,
                                "timestamp": timestamp
                            })
                            self.state["last_auto_compact_check"][agent_id] = timestamp
        except Exception as e:
            print(f"Error reading auto-compact log: {e}")
        
        return new_events
    
    def send_agent_message(self, agent_id: str, message: str):
        """エージェントにメッセージを送信"""
        cmd = ["./communication/agent-send.sh", agent_id, message]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  cwd=self.project_root)
            if result.returncode == 0:
                print(f"✓ Message sent to {agent_id}")
            else:
                print(f"✗ Failed to send message to {agent_id}: {result.stderr}")
        except Exception as e:
            print(f"✗ Error sending message to {agent_id}: {e}")
    
    def handle_auto_compact(self, agent_id: str):
        """auto-compact後のエージェントに再読み込みを指示"""
        message = (
            f"[{self.se_agent_id}] auto-compactを検知しました。"
            "プロジェクトの継続性のため、以下のファイルを再読み込みしてください：\n"
            "- CLAUDE.md（共通ルール）\n"
            f"- instructions/{agent_id.split('.')[0]}.md（あなたの役割）\n"
            "- 現在のディレクトリのchanges.md（進捗状況）\n"
            "- Agent-shared/directory_map.txt（エージェント配置）"
        )
        self.send_agent_message(agent_id, message)
    
    def check_agent_activity(self) -> Dict[str, datetime]:
        """各エージェントの最終活動時刻を確認"""
        activity = {}
        
        # changes.mdの更新時刻をチェック
        for changes_file in self.project_root.rglob("changes.md"):
            # Agent-shared内は除外
            if "Agent-shared" in str(changes_file):
                continue
            
            # ディレクトリ名からエージェントIDを推測
            parent_dir = changes_file.parent.name
            agent_match = re.match(r'(PG|CI|SE|CD|ID)\d*(\.\d+)*', parent_dir)
            
            if agent_match:
                agent_id = agent_match.group(0)
                mtime = datetime.fromtimestamp(changes_file.stat().st_mtime, tz=timezone.utc)
                
                # より新しい時刻で更新
                if agent_id not in activity or mtime > activity[agent_id]:
                    activity[agent_id] = mtime
        
        return activity
    
    def check_inactive_agents(self, activity: Dict[str, datetime]):
        """非アクティブなエージェントを検出して対応"""
        now = datetime.now(timezone.utc)
        
        for agent_id, last_active in activity.items():
            inactive_duration = now - last_active
            
            if inactive_duration > self.INACTIVITY_THRESHOLD:
                # 既に警告済みかチェック
                warn_info = self.state["warned_agents"].get(agent_id, {})
                
                if not warn_info:
                    # 初回警告
                    message = (
                        f"[{self.se_agent_id}] 作業状況を確認させてください。"
                        "現在の進捗を教えてください。"
                    )
                    self.send_agent_message(agent_id, message)
                    
                    self.state["warned_agents"][agent_id] = {
                        "first_warning": now.isoformat(),
                        "pm_notified": False
                    }
                    
                elif not warn_info["pm_notified"]:
                    # 警告から5分経過後、応答がなければPMに報告
                    first_warning = datetime.fromisoformat(warn_info["first_warning"])
                    if now - first_warning > self.RESPONSE_WAIT_TIME:
                        message = (
                            f"[{self.se_agent_id}] {agent_id}が"
                            f"{int(inactive_duration.total_seconds() / 60)}分以上無応答です。"
                            "確認をお願いします。"
                        )
                        self.send_agent_message("PM", message)
                        
                        self.state["warned_agents"][agent_id]["pm_notified"] = True
            else:
                # アクティブになったら警告状態をクリア
                if agent_id in self.state["warned_agents"]:
                    del self.state["warned_agents"][agent_id]
    
    def check_deviant_behavior(self) -> List[Tuple[str, str]]:
        """逸脱行動を検出（簡易版）"""
        deviations = []
        
        # ディレクトリ構造から逸脱を検出
        # 例: OpenMP/ディレクトリ内でMPIコードが生成されている
        for code_file in self.project_root.rglob("*.c"):
            if "Agent-shared" in str(code_file) or "BaseCode" in str(code_file):
                continue
            
            # ディレクトリ名から期待される技術を推定
            path_parts = code_file.parts
            expected_tech = None
            
            for part in path_parts:
                if "OpenMP" in part and "MPI" not in part:
                    expected_tech = "OpenMP"
                    break
                elif "MPI" in part and "OpenMP" not in part:
                    expected_tech = "MPI"
                    break
                elif "CUDA" in part:
                    expected_tech = "CUDA"
                    break
            
            if expected_tech:
                # ファイル内容を簡易チェック（最初の100行）
                try:
                    with open(code_file, 'r', encoding='utf-8') as f:
                        content = f.read(5000)  # 最初の5000文字
                        
                        # 逸脱の検出
                        if expected_tech == "OpenMP" and "MPI_Init" in content:
                            agent_id = self.guess_agent_from_path(code_file)
                            if agent_id:
                                deviations.append((agent_id, 
                                    f"OpenMP担当なのにMPIコードを実装: {code_file}"))
                        
                        elif expected_tech == "MPI" and "#pragma omp" in content:
                            agent_id = self.guess_agent_from_path(code_file)
                            if agent_id:
                                deviations.append((agent_id, 
                                    f"MPI担当なのにOpenMPコードを実装: {code_file}"))
                
                except Exception:
                    pass
        
        return deviations
    
    def guess_agent_from_path(self, file_path: Path) -> Optional[str]:
        """ファイルパスからエージェントIDを推定"""
        for part in file_path.parts:
            match = re.match(r'(PG|CI)\d*(\.\d+)*', part)
            if match:
                return match.group(0)
        return None
    
    def generate_monitoring_report(self) -> str:
        """監視レポートを生成"""
        report = f"# Agent Monitoring Report\n"
        report += f"Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        # コンテキスト使用率
        context_usage = self.get_latest_context_usage()
        if context_usage:
            report += "## Context Usage Status\n"
            for agent_id, usage in sorted(context_usage.items(), 
                                        key=lambda x: x[1], reverse=True):
                status = "⚠️ CRITICAL" if usage >= 95 else "✓"
                report += f"- {agent_id}: {usage:.1f}% {status}\n"
            report += "\n"
        
        # 非アクティブエージェント
        if self.state["warned_agents"]:
            report += "## Inactive Agents\n"
            for agent_id, info in self.state["warned_agents"].items():
                pm_status = "PM notified" if info["pm_notified"] else "Warning sent"
                report += f"- {agent_id}: {pm_status}\n"
            report += "\n"
        
        # auto-compactイベント
        if self.state["last_auto_compact_check"]:
            report += "## Recent Auto-compact Events\n"
            for agent_id, timestamp in sorted(self.state["last_auto_compact_check"].items(), 
                                            key=lambda x: x[1], reverse=True)[:5]:
                report += f"- {agent_id}: {timestamp}\n"
            report += "\n"
        
        return report
    
    def run_monitoring_cycle(self):
        """監視サイクルを1回実行"""
        print(f"\n🔍 Starting monitoring cycle at {datetime.now()}")
        
        # 1. コンテキスト使用率チェック
        context_usage = self.get_latest_context_usage()
        for agent_id, usage in context_usage.items():
            if usage >= self.CONTEXT_WARNING_THRESHOLD:
                print(f"⚠️  {agent_id} is at {usage:.1f}% context usage!")
        
        # 2. auto-compactイベントチェック
        new_events = self.check_auto_compact_events()
        for event in new_events:
            print(f"🔄 Auto-compact detected for {event['agent_id']}")
            self.handle_auto_compact(event['agent_id'])
        
        # 3. エージェント活動チェック
        activity = self.check_agent_activity()
        self.check_inactive_agents(activity)
        
        # 4. 逸脱行動チェック
        deviations = self.check_deviant_behavior()
        for agent_id, issue in deviations:
            print(f"⚠️  Deviation detected: {agent_id} - {issue}")
            message = f"[{self.se_agent_id}] 逸脱を検知しました: {issue}"
            self.send_agent_message(agent_id, message)
        
        # 5. 状態を保存
        self.save_state()
        
        # 6. レポート生成
        report = self.generate_monitoring_report()
        report_file = self.telemetry_dir / "monitoring_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ Monitoring cycle complete. Report saved to {report_file}")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor agent health and activity')
    parser.add_argument('--se-id', default='SE1', help='SE agent ID')
    parser.add_argument('--once', action='store_true', 
                       help='Run once instead of continuous monitoring')
    parser.add_argument('--interval', type=int, default=300, 
                       help='Monitoring interval in seconds (default: 300)')
    
    args = parser.parse_args()
    
    monitor = AgentMonitor(se_agent_id=args.se_id)
    
    if args.once:
        # 1回だけ実行
        monitor.run_monitoring_cycle()
    else:
        # 継続的に監視
        print(f"Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                monitor.run_monitoring_cycle()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")


if __name__ == "__main__":
    main()