#!/usr/bin/env python3
"""
changes.mdレポート生成ツール
複数のPGエージェントのchanges.mdを解析し、統合レポートを生成する
"""

import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

class ChangesReportGenerator:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.reports_dir = self.project_root / "Agent-shared" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def find_changes_files(self) -> List[Path]:
        """プロジェクト内の全てのchanges.mdファイルを検索"""
        changes_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Agent-shared, GitHub, BaseCodeは除外
            if any(skip in root for skip in ["Agent-shared", "GitHub", "BaseCode"]):
                continue
            if "changes.md" in files:
                changes_files.append(Path(root) / "changes.md")
        return changes_files
    
    def parse_changes_entry(self, content: str) -> List[Dict]:
        """changes.mdのエントリをパース"""
        entries = []
        # version: v1.2.3 のパターンでエントリを分割
        version_pattern = r'(?:^|\n)(?:##?\s*)?version:\s*(v[\d.]+)'
        
        # エントリごとに分割
        splits = re.split(version_pattern, content)
        
        # 最初の要素は空またはヘッダーなのでスキップ
        for i in range(1, len(splits), 2):
            if i+1 < len(splits):
                version = splits[i]
                entry_content = splits[i+1]
                
                entry = {"version": version}
                
                # 各フィールドを抽出
                patterns = {
                    "change_summary": r'change_summary:\s*"([^"]*)"',
                    "timestamp": r'timestamp:\s*"([^"]*)"',
                    "compile_status": r'compile_status:\s*(\w+)',
                    "job_status": r'job_status:\s*(\w+)',
                    "performance_metric": r'performance_metric:\s*"([^"]*)"',
                    "compute_cost": r'compute_cost:\s*"([^"]*)"',
                    "sota_level": r'sota_level:\s*(\w+)',
                    "technical_comment": r'technical_comment:\s*"([^"]*)"'
                }
                
                for field, pattern in patterns.items():
                    match = re.search(pattern, entry_content)
                    if match:
                        entry[field] = match.group(1)
                
                entries.append(entry)
        
        return entries
    
    def extract_agent_info(self, file_path: Path) -> Tuple[str, str]:
        """ファイルパスからエージェント情報を抽出"""
        parts = file_path.parts
        
        # PGエージェントを探す
        pg_agent = None
        tech_stack = []
        
        for i, part in enumerate(parts):
            if "PG" in part and re.match(r'.*PG\d+\.\d+\.\d+', part):
                pg_agent = part
            # 技術スタック（OpenMP, MPI, CUDA等）を抽出
            if part in ["OpenMP", "MPI", "CUDA", "OpenACC", "AVX512"]:
                tech_stack.append(part)
            elif "_" in part and any(tech in part for tech in ["OpenMP", "MPI", "CUDA"]):
                tech_stack.extend(part.split("_"))
        
        tech = "_".join(tech_stack) if tech_stack else "unknown"
        return pg_agent or "unknown", tech
    
    def generate_daily_summary(self, all_entries: Dict[str, List[Dict]]) -> str:
        """日次サマリーレポートを生成"""
        now = datetime.now(timezone.utc)
        report = f"# Daily Summary Report - {now.strftime('%Y-%m-%d')}\n\n"
        report += f"Generated at: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        # 統計情報
        report += "## 📊 Overall Statistics\n\n"
        
        total_attempts = 0
        successful_runs = 0
        compile_failures = 0
        runtime_failures = 0
        sota_updates = defaultdict(int)
        
        for agent, entries in all_entries.items():
            total_attempts += len(entries)
            for entry in entries:
                if entry.get("compile_status") == "success":
                    if entry.get("job_status") == "completed":
                        successful_runs += 1
                    else:
                        runtime_failures += 1
                else:
                    compile_failures += 1
                
                sota = entry.get("sota_level", "none")
                if sota != "none":
                    sota_updates[sota] += 1
        
        success_rate = (successful_runs / total_attempts * 100) if total_attempts > 0 else 0
        
        report += f"- Total attempts: {total_attempts}\n"
        report += f"- Successful runs: {successful_runs} ({success_rate:.1f}%)\n"
        report += f"- Compile failures: {compile_failures}\n"
        report += f"- Runtime failures: {runtime_failures}\n\n"
        
        report += "## 🏆 SOTA Updates\n\n"
        for level in ["local", "parent", "global", "project"]:
            count = sota_updates.get(level, 0)
            report += f"- {level.capitalize()}: {count}\n"
        
        report += "\n## 📈 Agent Performance\n\n"
        report += "| Agent | Attempts | Success | Rate | SOTA |\n"
        report += "|-------|----------|---------|------|------|\n"
        
        for agent, entries in sorted(all_entries.items()):
            attempts = len(entries)
            successes = sum(1 for e in entries if e.get("compile_status") == "success" and e.get("job_status") == "completed")
            rate = (successes / attempts * 100) if attempts > 0 else 0
            sotas = sum(1 for e in entries if e.get("sota_level") and e.get("sota_level") != "none")
            report += f"| {agent} | {attempts} | {successes} | {rate:.1f}% | {sotas} |\n"
        
        return report
    
    def generate_tech_progress_report(self, tech_entries: Dict[str, List[Dict]]) -> str:
        """技術別進捗レポートを生成"""
        now = datetime.now(timezone.utc)
        report = f"# Technology Progress Report - {now.strftime('%Y-%m-%d')}\n\n"
        report += f"Generated at: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        report += "## 🔧 Technology Performance\n\n"
        report += "| Technology | Attempts | Success Rate | Best Performance | SOTA Count |\n"
        report += "|------------|----------|--------------|------------------|------------|\n"
        
        for tech, entries in sorted(tech_entries.items()):
            attempts = len(entries)
            successes = sum(1 for e in entries if e.get("compile_status") == "success" and e.get("job_status") == "completed")
            rate = (successes / attempts * 100) if attempts > 0 else 0
            
            # 最高性能を抽出
            best_perf = "N/A"
            perfs = [e.get("performance_metric", "") for e in entries if e.get("performance_metric")]
            if perfs:
                # GFLOPS値を抽出して比較
                gflops_values = []
                for perf in perfs:
                    match = re.search(r'([\d.]+)\s*GFLOPS', perf)
                    if match:
                        gflops_values.append(float(match.group(1)))
                if gflops_values:
                    best_perf = f"{max(gflops_values):.1f} GFLOPS"
            
            sotas = sum(1 for e in entries if e.get("sota_level") and e.get("sota_level") != "none")
            report += f"| {tech} | {attempts} | {rate:.1f}% | {best_perf} | {sotas} |\n"
        
        return report
    
    def generate_reports(self):
        """全てのレポートを生成"""
        print("🔍 Searching for changes.md files...")
        changes_files = self.find_changes_files()
        print(f"Found {len(changes_files)} changes.md files")
        
        # エージェント別と技術別にエントリを集計
        agent_entries = defaultdict(list)
        tech_entries = defaultdict(list)
        
        for file_path in changes_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                entries = self.parse_changes_entry(content)
                agent, tech = self.extract_agent_info(file_path)
                
                agent_entries[agent].extend(entries)
                tech_entries[tech].extend(entries)
                
                print(f"✓ Processed: {file_path} ({len(entries)} entries)")
            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")
        
        # レポート生成
        now = datetime.now(timezone.utc)
        date_str = now.strftime('%Y%m%d')
        
        # 日次サマリー
        daily_report = self.generate_daily_summary(agent_entries)
        daily_path = self.reports_dir / f"daily_summary_{date_str}.md"
        with open(daily_path, 'w', encoding='utf-8') as f:
            f.write(daily_report)
        print(f"\n📄 Generated: {daily_path}")
        
        # 技術別進捗
        tech_report = self.generate_tech_progress_report(tech_entries)
        tech_path = self.reports_dir / f"tech_progress_{date_str}.md"
        with open(tech_path, 'w', encoding='utf-8') as f:
            f.write(tech_report)
        print(f"📄 Generated: {tech_path}")
        
        return daily_path, tech_path

if __name__ == "__main__":
    # プロジェクトルートから実行
    generator = ChangesReportGenerator()
    generator.generate_reports()