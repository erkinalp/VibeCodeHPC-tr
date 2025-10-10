#!/usr/bin/env python3
"""
SOTA Management System - VibeCodeHPC

4階層SOTAYönetimシステム (Local/Parent/Global/Project)
"""

import os
import json
from pathlib import Path
import glob

class SOTAChecker:
    def __init__(self, current_dir):
        self.current_dir = Path(current_dir).resolve()  # 絶対パスに変換
        self.performance = None
        
    def check_sota_levels(self, performance_metric):
        """全階層でのSOTA判定"""
        self.performance = float(performance_metric.split()[0])
        
        results = {
            'local': self.check_local_sota(),
            'parent': self.check_parent_sota(),
            'hardware': self.check_hardware_sota(),
            'project': self.check_project_sota()
        }
        
        return results
    
    def check_local_sota(self):
        """Local SOTA判定"""
        sota_file = self.current_dir / "sota_local.txt"
        if not sota_file.exists():
            return True  # 初回は必ずSOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def check_parent_sota(self):
        """Parent SOTA判定（Virtual算出）"""
        # PG_visible_dir.mdDosyaを探す
        visible_file = self.current_dir / "PG_visible_dir.md"
        if not visible_file.exists():
            return False
            
        virtual_parent_paths = self._parse_virtual_parent_paths(visible_file)
        
        max_parent_perf = 0.0
        for path in virtual_parent_paths:
            full_path = self.current_dir / path
            if full_path.exists():
                for sota_file in full_path.glob("*/sota_local.txt"):
                    with open(sota_file, 'r') as f:
                        perf = float(f.readline().split('"')[1].split()[0])
                        max_parent_perf = max(max_parent_perf, perf)
        
        return self.performance > max_parent_perf
    
    def _parse_virtual_parent_paths(self, md_file):
        """markdownから Virtual parent セクションの📁付きYolを抽出"""
        with open(md_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        virtual_parent_section = False
        paths = []
        
        for line in lines:
            line = line.strip()
            if "### Virtual parent" in line:
                virtual_parent_section = True
                continue
            elif line.startswith("###") and virtual_parent_section:
                break  # 次のセクションに入ったら終了
            elif virtual_parent_section and line.startswith("../") and "📁" in line:
                # ../MPI📁 から ../MPI を抽出
                path = line.split("📁")[0]
                paths.append(path)
        
        return paths
    
    def check_hardware_sota(self):
        """Hardware SOTA判定"""
        # hardware_info.txt階層のsota_hardware.txtをKontrol
        hardware_dir = self.find_hardware_info_dir()
        if not hardware_dir:
            return False
            
        sota_file = hardware_dir / "sota_hardware.txt"
        if not sota_file.exists():
            return True  # 初回は必ずSOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def check_project_sota(self):
        """Project SOTA判定"""
        # VibeCodeHPCルートのsota_project.txtをKontrol
        project_root = self.find_project_root()
        if not project_root:
            return False
            
        sota_file = project_root / "sota_project.txt"
        
        if not sota_file.exists():
            return True  # 初回は必ずSOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def find_hardware_info_dir(self):
        """hardware_info.mdが存在するDizinを探す"""
        current = self.current_dir
        while current != current.parent:
            if (current / "hardware_info.md").exists():
                return current
            current = current.parent
        return None
    
    def find_project_root(self):
        """VibeCodeHPCルートを探す"""
        current = self.current_dir
        while current != current.parent:
            if current.name.startswith("VibeCodeHPC"):
                return current
            current = current.parent
        return None
    
    def update_sota_files(self, version, timestamp, agent_id):
        """SOTAGüncelleme時の各階層DosyaGüncelleme"""
        sota_info = {
            'local': self.check_local_sota(),
            'parent': self.check_parent_sota(),
            'hardware': self.check_hardware_sota(),
            'project': self.check_project_sota()
        }
        
        # LocalGüncelleme
        if sota_info['local']:
            self.update_local_sota(version, timestamp, agent_id)
        
        # HardwareGüncelleme
        if sota_info['hardware']:
            self.update_hardware_sota(version, timestamp, agent_id)
        
        # ProjectGüncelleme
        if sota_info['project']:
            self.update_project_sota(version, timestamp, agent_id)
        
        return sota_info
    
    def update_local_sota(self, version, timestamp, agent_id):
        """Local SOTADosyaGüncelleme"""
        sota_file = self.current_dir / "sota_local.txt"
        with open(sota_file, 'w') as f:
            f.write(f'current_best: "{self.performance} GFLOPS"\n')
            f.write(f'achieved_by: "{version}"\n')
            f.write(f'timestamp: "{timestamp}"\n')
            f.write(f'agent_id: "{agent_id}"\n')
    
    def update_hardware_sota(self, version, timestamp, agent_id):
        """Hardware SOTADosyaGüncelleme"""
        hardware_dir = self.find_hardware_info_dir()
        if hardware_dir:
            sota_file = hardware_dir / "sota_hardware.txt"
            with open(sota_file, 'w') as f:
                f.write(f'current_best: "{self.performance} GFLOPS"\n')
                f.write(f'achieved_by: "{agent_id}"\n')
                f.write(f'timestamp: "{timestamp}"\n')
                f.write(f'hardware_path: "{self.get_hardware_path()}"\n')
                f.write(f'strategy: "{self.get_strategy()}"\n')
    
    def update_project_sota(self, version, timestamp, agent_id):
        """Project SOTADosyaGüncelleme"""
        project_root = self.find_project_root()
        if project_root:
            sota_file = project_root / "sota_project.txt"
            with open(sota_file, 'w') as f:
                f.write(f'current_best: "{self.performance} GFLOPS"\n')
                f.write(f'achieved_by: "{agent_id}"\n')
                f.write(f'timestamp: "{timestamp}"\n')
                f.write(f'hardware_path: "{self.get_hardware_path()}"\n')
                f.write(f'strategy: "{self.get_strategy()}"\n')
            
            # 履歴にも追記
            history_file = project_root / "history" / "sota_project_history.txt"
            history_file.parent.mkdir(exist_ok=True)
            with open(history_file, 'a') as f:
                f.write(f'[{timestamp}] {self.performance} GFLOPS by {agent_id} ({self.get_strategy()})\n')

    def get_hardware_path(self):
        """ハードウェアYolをAlma"""
        # Projeルートからの相対Yolを算出
        project_root = self.find_project_root()
        if project_root:
            relative_path = self.current_dir.relative_to(project_root)
            return str(relative_path.parent)
        return "unknown"
    
    def get_strategy(self):
        """戦略名をAlma"""
        # 現在のDizinYolから戦略を推定
        path_parts = self.current_dir.parts
        if len(path_parts) >= 2:
            return path_parts[-2]  # 親ディレクトリ名が戦略名
        return "unknown"

def get_virtual_parent_sota(current_dir):
    """
    Virtual Parent SOTA算出の独立Fonksiyon
    PG_visible_dir.mdから Virtual parent セクションの📁付きYolをOkuma
    
    Örnek：OpenMP_MPI📁の場合、../MPI📁と../OpenMP📁を参照
    """
    current_path = Path(current_dir)
    
    # PG_visible_dir.mdDosyaを探す
    visible_file = current_path / "PG_visible_dir.md"
    if not visible_file.exists():
        return 0.0, None
    
    # Virtual parent Yolを抽出
    def parse_virtual_parent_paths(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        virtual_parent_section = False
        paths = []
        
        for line in lines:
            line = line.strip()
            if "### Virtual parent" in line:
                virtual_parent_section = True
                continue
            elif line.startswith("###") and virtual_parent_section:
                break
            elif virtual_parent_section and line.startswith("../") and "📁" in line:
                path = line.split("📁")[0]
                paths.append(path)
        
        return paths
    
    virtual_parent_paths = parse_virtual_parent_paths(visible_file)
    
    parent_sota = 0.0
    best_info = None
    
    for path in virtual_parent_paths:
        full_path = current_path / path
        if full_path.exists():
            # 親世代Dizin内のPGDizinを探索
            for sota_file in full_path.glob("*/sota_local.txt"):
                try:
                    with open(sota_file, 'r') as f:
                        perf = float(f.readline().split('"')[1].split()[0])
                        if perf > parent_sota:
                            parent_sota = perf
                            best_info = str(sota_file)
                except (ValueError, IndexError):
                    continue
    
    return parent_sota, best_info

# CLIYürütme対応
if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python sota_checker.py <性能値> [ディレクトリ] [バージョン] [agent_id]")
        print("  例: python sota_checker.py '350.0 GFLOPS'")
        print("  例: python sota_checker.py '350.0 GFLOPS' . v1.2.3 PG1.1")
        sys.exit(1)
    
    performance = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    version = sys.argv[3] if len(sys.argv) > 3 else "unknown"
    agent_id = sys.argv[4] if len(sys.argv) > 4 else "unknown"
    
    checker = SOTAChecker(directory)
    results = checker.check_sota_levels(performance)
    
    print(f"SOTA判定結果 ({performance}):")
    for level, is_sota in results.items():
        status = "✓ NEW SOTA!" if is_sota else "- no update"
        print(f"  {level:10s}: {status}")
    
    # SOTAGüncellemeがあればKayıt
    if any(results.values()):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        checker.update_sota_files(version, timestamp, agent_id)
        print(f"\nSOTAファイル更新完了 (timestamp: {timestamp})")