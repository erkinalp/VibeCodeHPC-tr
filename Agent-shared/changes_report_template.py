#!/usr/bin/env python3
"""
changes.mdレポート生成テンプレート
SEエージェントが必要に応じてカスタマイズして使用する汎用的なレポート生成ツール
"""

import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

class ChangesReportTemplate:
    """
    汎用的なchanges.md解析・レポート生成クラス
    SEエージェントが継承・カスタマイズして使用することを想定
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.reports_dir = self.project_root / "Agent-shared" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def find_target_files(self, filename: str = "changes.md", 
                         exclude_dirs: List[str] = ["Agent-shared", "GitHub", "BaseCode"]) -> List[Path]:
        """
        プロジェクト内の対象ファイルを検索
        
        Args:
            filename: 検索するファイル名
            exclude_dirs: 除外するディレクトリのリスト
        """
        target_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 除外ディレクトリをスキップ
            if any(skip in root for skip in exclude_dirs):
                continue
            if filename in files:
                target_files.append(Path(root) / filename)
        return target_files
    
    def parse_entry(self, content: str) -> List[Dict[str, Any]]:
        """
        ファイル内容をパース（カスタマイズ可能）
        デフォルトではchanges.mdの標準フォーマットをパース
        """
        entries = []
        # version: v1.2.3 のパターンでエントリを分割
        version_pattern = r'(?:^|\n)(?:##?\s*)?version:\s*(v[\d.]+)'
        
        # エントリごとに分割
        splits = re.split(version_pattern, content)
        
        for i in range(1, len(splits), 2):
            if i+1 < len(splits):
                version = splits[i]
                entry_content = splits[i+1]
                
                entry = {"version": version}
                
                # 標準フィールドの抽出（必要に応じて追加・変更可能）
                patterns = {
                    "change_summary": r'change_summary:\s*"([^"]*)"',
                    "timestamp": r'timestamp:\s*"([^"]*)"',
                    "compile_status": r'compile_status:\s*(\w+)',
                    "job_status": r'job_status:\s*(\w+)',
                    "performance_metric": r'performance_metric:\s*"([^"]*)"',
                    "sota_level": r'sota_level:\s*(\w+)',
                    "technical_comment": r'technical_comment:\s*"([^"]*)"'
                }
                
                for field, pattern in patterns.items():
                    match = re.search(pattern, entry_content)
                    if match:
                        entry[field] = match.group(1)
                
                entries.append(entry)
        
        return entries
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        ファイルパスからメタデータを抽出（カスタマイズ推奨）
        
        Returns:
            抽出したメタデータの辞書
        """
        parts = file_path.parts
        metadata = {
            "file_path": str(file_path),
            "directory_path": str(file_path.parent),
            "path_components": list(parts),
        }
        
        # エージェント名の抽出（PG, CI, SE等）
        for part in parts:
            if re.match(r'(PG|CI|SE|CD|ID|PM)\d*(\.\d+)*', part):
                metadata["agent"] = part
                break
        
        # ディレクトリ構造から追加情報を抽出
        # SEエージェントがプロジェクトに応じてカスタマイズ
        
        return metadata
    
    def aggregate_data(self, all_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        データを集計（カスタマイズ推奨）
        
        Args:
            all_data: ファイルパスをキー、エントリリストを値とする辞書
            
        Returns:
            集計結果の辞書
        """
        stats = {
            "total_entries": 0,
            "by_status": defaultdict(int),
            "by_agent": defaultdict(lambda: {"total": 0, "success": 0}),
            "sota_updates": defaultdict(int),
            "timeline": []
        }
        
        for file_path, entries in all_data.items():
            for entry in entries:
                stats["total_entries"] += 1
                
                # コンパイルステータス別集計
                compile_status = entry.get("compile_status", "unknown")
                stats["by_status"][compile_status] += 1
                
                # SOTA更新の集計
                sota_level = entry.get("sota_level", "none")
                if sota_level != "none":
                    stats["sota_updates"][sota_level] += 1
                
                # タイムライン用データ
                if "timestamp" in entry:
                    stats["timeline"].append({
                        "timestamp": entry["timestamp"],
                        "version": entry.get("version", "unknown"),
                        "status": compile_status,
                        "file": str(file_path)
                    })
        
        # タイムラインをソート
        stats["timeline"].sort(key=lambda x: x["timestamp"])
        
        return stats
    
    def generate_report(self, stats: Dict[str, Any], report_type: str = "summary") -> str:
        """
        レポートを生成（カスタマイズ推奨）
        
        Args:
            stats: 集計データ
            report_type: レポートの種類
        """
        now = datetime.now(timezone.utc)
        report = f"# Changes Report - {report_type.title()}\n\n"
        report += f"Generated at: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        # 基本統計
        report += "## 📊 Summary\n\n"
        report += f"- Total entries: {stats['total_entries']}\n"
        
        # ステータス別
        report += "\n### Status Breakdown\n"
        for status, count in stats['by_status'].items():
            percentage = (count / stats['total_entries'] * 100) if stats['total_entries'] > 0 else 0
            report += f"- {status}: {count} ({percentage:.1f}%)\n"
        
        # SOTA更新
        if stats['sota_updates']:
            report += "\n### SOTA Updates\n"
            for level, count in stats['sota_updates'].items():
                report += f"- {level}: {count}\n"
        
        return report
    
    def run(self, custom_params: Dict[str, Any] = None):
        """
        レポート生成を実行
        
        Args:
            custom_params: カスタムパラメータ
        """
        params = custom_params or {}
        
        # ファイル検索
        target_files = self.find_target_files(
            filename=params.get("filename", "changes.md"),
            exclude_dirs=params.get("exclude_dirs", ["Agent-shared", "GitHub", "BaseCode"])
        )
        
        print(f"Found {len(target_files)} target files")
        
        # データ収集
        all_data = {}
        for file_path in target_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                entries = self.parse_entry(content)
                if entries:
                    all_data[str(file_path)] = entries
                    print(f"✓ Processed: {file_path} ({len(entries)} entries)")
                    
            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")
        
        # 集計
        stats = self.aggregate_data(all_data)
        
        # レポート生成
        report = self.generate_report(stats)
        
        # ファイル保存
        now = datetime.now(timezone.utc)
        report_path = self.reports_dir / f"report_{now.strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {report_path}")
        return report_path


# 使用例（SEエージェントがカスタマイズして使用）
class HPCOptimizationReport(ChangesReportTemplate):
    """HPC最適化プロジェクト用のカスタマイズ例"""
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """プロジェクト固有のメタデータ抽出"""
        metadata = super().extract_metadata(file_path)
        
        # ディレクトリ名から技術を動的に抽出
        parts = file_path.parts
        technologies = []
        
        for part in parts:
            # アンダースコア区切りの技術名を分解
            if "_" in part:
                potential_techs = part.split("_")
                technologies.extend(potential_techs)
            else:
                technologies.append(part)
        
        # よく知られた技術名をフィルタ（必要に応じて追加）
        known_techs = ["OpenMP", "MPI", "CUDA", "OpenACC", "AVX", "AVX2", "AVX512"]
        found_techs = [t for t in technologies if any(k in t for k in known_techs)]
        
        if found_techs:
            metadata["technologies"] = found_techs
        
        return metadata


if __name__ == "__main__":
    # 基本的な使用
    reporter = ChangesReportTemplate()
    reporter.run()
    
    # カスタマイズした使用
    # hpc_reporter = HPCOptimizationReport()
    # hpc_reporter.run()