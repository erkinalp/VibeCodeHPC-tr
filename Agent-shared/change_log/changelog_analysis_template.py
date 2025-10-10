#!/usr/bin/env python3
"""
ChangeLog.md解析テンプレート
SEAjanが必要に応じてカスタマイズして使用する汎用的な解析ツール

配置場所: Agent-shared/tools/changelog_analyzer.py
出力先: Agent-shared/reports/ (技術的な解析結果)

Dikkat: これは一次レポート(ChangeLog.md)を解析するツールです。
二次レポート(User-shared/reports/)はSEが手動でOluşturmaします。
"""

import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

class ChangeLogAnalysisTemplate:
    """
    汎用的なChangeLog.md解析クラス
    SEAjanが継承・カスタマイズして使用することを想定
    
    このクラスは技術的な解析を行うためのもので、
    人間向けの二次レポートOluşturmaは別途手動で行います。
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.reports_dir = self.project_root / "Agent-shared" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def find_target_files(self, filename: str = "ChangeLog.md", 
                         exclude_dirs: List[str] = ["Agent-shared", "GitHub", "BaseCode"]) -> List[Path]:
        """
        Proje内の対象Dosyaを検索
        
        Args:
            filename: 検索するDosya名
            exclude_dirs: 除外するDizinのリスト
        """
        target_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 除外Dizinをスキップ
            if any(skip in root for skip in exclude_dirs):
                continue
            if filename in files:
                target_files.append(Path(root) / filename)
        return target_files
    
    def parse_entry(self, content: str) -> List[Dict[str, Any]]:
        """
        Dosya内容をパース（カスタマイズ可能）
        ChangeLog.mdの新フォーマットをパース
        """
        entries = []
        
        # ### v1.2.3 のパターンでエントリを分割
        version_pattern = r'###\s+v([\d.]+)'
        
        # エントリごとに分割
        matches = list(re.finditer(version_pattern, content))
        
        for i, match in enumerate(matches):
            version = f"v{match.group(1)}"
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(content)
            entry_content = content[start:end]
            
            entry = {"version": version}
            
            # 新フォーマットのフィールドを抽出
            # Değişiklik点、結果、コメント
            change_match = re.search(r'\*\*変更点\*\*:\s*"([^"]+)"', entry_content)
            if change_match:
                entry["change_summary"] = change_match.group(1)
            
            result_match = re.search(r'\*\*結果\*\*:\s*([^`]+)\s*`([^`]+)`', entry_content)
            if result_match:
                entry["result_type"] = result_match.group(1).strip()
                entry["result_value"] = result_match.group(2).strip()
            
            comment_match = re.search(r'\*\*コメント\*\*:\s*"([^"]+)"', entry_content)
            if comment_match:
                entry["technical_comment"] = comment_match.group(1)
            
            # <details>内の情報をパース
            details_match = re.search(r'<details>([\s\S]*?)</details>', entry_content)
            if details_match:
                details_content = details_match.group(1)
                
                # compile情報
                compile_match = re.search(r'-\s*\[([x\s])\]\s*\*\*compile\*\*[\s\S]*?status:\s*`([^`]+)`', details_content)
                if compile_match:
                    entry["compile_complete"] = compile_match.group(1) == 'x'
                    entry["compile_status"] = compile_match.group(2)
                
                # job情報
                job_match = re.search(r'-\s*\[([x\s])\]\s*\*\*job\*\*[\s\S]*?status:\s*`([^`]+)`', details_content)
                if job_match:
                    entry["job_complete"] = job_match.group(1) == 'x'
                    entry["job_status"] = job_match.group(2)
                
                # test情報
                test_match = re.search(r'-\s*\[([x\s])\]\s*\*\*test\*\*[\s\S]*?status:\s*`([^`]+)`', details_content)
                if test_match:
                    entry["test_complete"] = test_match.group(1) == 'x'
                    entry["test_status"] = test_match.group(2)
                
                # performance
                perf_match = re.search(r'performance:\s*`([^`]+)`', details_content)
                if perf_match:
                    entry["performance"] = perf_match.group(1)
                
                # sota
                sota_match = re.search(r'-\s*\[x\]\s*\*\*sota\*\*[\s\S]*?scope:\s*`([^`]+)`', details_content)
                if sota_match:
                    entry["sota_scope"] = sota_match.group(1)
            
            entries.append(entry)
        
        return entries
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        DosyaYolからメタVeriを抽出（カスタマイズÖnerilen）
        
        Returns:
            抽出したメタVeriの辞書
        """
        parts = file_path.parts
        metadata = {
            "file_path": str(file_path),
            "directory_path": str(file_path.parent),
            "path_components": list(parts),
        }
        
        # Ajan名の抽出（PG, SE等）
        for part in parts:
            if re.match(r'(PG|SE|CD|PM)\d*(\.\d+)*', part):
                metadata["agent"] = part
                break
        
        # Dizin構造からEkleme情報を抽出
        # SEAjanがProjeに応じてカスタマイズ
        
        return metadata
    
    def aggregate_data(self, all_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Veriを集計（カスタマイズÖnerilen）
        
        Args:
            all_data: DosyaYolをキー、エントリリストを値とする辞書
            
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
                
                # SOTAGüncellemeの集計
                sota_scope = entry.get("sota_scope")
                if sota_scope:
                    stats["sota_updates"][sota_scope] += 1
                
                # タイムライン用Veri
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
        レポートをÜretim（カスタマイズÖnerilen）
        
        Args:
            stats: 集計Veri
            report_type: レポートの種類
        """
        now = datetime.now(timezone.utc)
        report = f"# ChangeLog Report - {report_type.title()}\n\n"
        report += f"Generated at: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        # 基本İstatistik
        report += "## 📊 Summary\n\n"
        report += f"- Total entries: {stats['total_entries']}\n"
        
        # ステータス別
        report += "\n### Status Breakdown\n"
        for status, count in stats['by_status'].items():
            percentage = (count / stats['total_entries'] * 100) if stats['total_entries'] > 0 else 0
            report += f"- {status}: {count} ({percentage:.1f}%)\n"
        
        # SOTAGüncelleme
        if stats['sota_updates']:
            report += "\n### SOTA Updates\n"
            for level, count in stats['sota_updates'].items():
                report += f"- {level}: {count}\n"
        
        return report
    
    def run(self, custom_params: Dict[str, Any] = None):
        """
        レポートÜretimをYürütme
        
        Args:
            custom_params: カスタムパラメータ
        """
        params = custom_params or {}
        
        # Dosya検索
        target_files = self.find_target_files(
            filename=params.get("filename", "ChangeLog.md"),
            exclude_dirs=params.get("exclude_dirs", ["Agent-shared", "GitHub", "BaseCode"])
        )
        
        print(f"Found {len(target_files)} target files")
        
        # Veri収集
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
        
        # レポートÜretim
        report = self.generate_report(stats)
        
        # DosyaKaydetme
        now = datetime.now(timezone.utc)
        report_path = self.reports_dir / f"report_{now.strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 Analysis report saved to: {report_path}")
        print(f"💡 Note: This is a technical analysis. For user-facing reports, create manually in User-shared/reports/")
        return report_path


# 使用Örnek（SEAjanがカスタマイズして使用）
class HPCOptimizationAnalysis(ChangeLogAnalysisTemplate):
    """HPCOptimizasyonProje用の解析カスタマイズÖrnek"""
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Proje固有のメタVeri抽出"""
        metadata = super().extract_metadata(file_path)
        
        # Dizin名から技術を動的に抽出
        parts = file_path.parts
        technologies = []
        
        for part in parts:
            # アンダースコア区切りの技術名を分解
            if "_" in part:
                potential_techs = part.split("_")
                technologies.extend(potential_techs)
            else:
                technologies.append(part)
        
        # よく知られた技術名をフィルタ（必要に応じてEkleme）
        known_techs = ["OpenMP", "MPI", "CUDA", "OpenACC", "AVX", "AVX2", "AVX512"]
        found_techs = [t for t in technologies if any(k in t for k in known_techs)]
        
        if found_techs:
            metadata["technologies"] = found_techs
        
        return metadata


if __name__ == "__main__":
    # 基本的な使用
    analyzer = ChangeLogAnalysisTemplate()
    analyzer.run()
    
    # カスタマイズした使用
    # hpc_analyzer = HPCOptimizationReport()
    # hpc_analyzer.run()
    
    # 注: このScriptはAgent-shared/tools/に配置することをÖnerilen