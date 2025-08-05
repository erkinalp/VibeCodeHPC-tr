#!/usr/bin/env python3
"""
SOTA Management System - OpenCodeAT

4階層SOTA管理システム (Local/Parent/Global/Project)
"""

import os
import json
from pathlib import Path
import glob

class SOTAChecker:
    def __init__(self, current_dir):
        self.current_dir = Path(current_dir)
        self.performance = None
        
    def check_sota_levels(self, performance_metric):
        """全階層でのSOTA判定"""
        self.performance = float(performance_metric.split()[0])
        
        results = {
            'local': self.check_local_sota(),
            'parent': self.check_parent_sota(),
            'global': self.check_global_sota(),
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
        # PG_visible_dir.mdファイルを探す
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
        """markdownから Virtual parent セクションの📁付きパスを抽出"""
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
    
    def check_global_sota(self):
        """Global SOTA判定"""
        # hardware_info.txt階層のsota_global.txtを確認
        hardware_dir = self.find_hardware_info_dir()
        if not hardware_dir:
            return False
            
        sota_file = hardware_dir / "sota_global.txt"
        if not sota_file.exists():
            return True  # 初回は必ずSOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def check_project_sota(self):
        """Project SOTA判定"""
        # OpenCodeATルートのsota_project.txtを確認
        project_root = self.find_project_root()
        sota_file = project_root / "sota_project.txt"
        
        if not sota_file.exists():
            return True  # 初回は必ずSOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def find_hardware_info_dir(self):
        """hardware_info.mdが存在するディレクトリを探す"""
        current = self.current_dir
        while current != current.parent:
            if (current / "hardware_info.md").exists():
                return current
            current = current.parent
        return None
    
    def find_project_root(self):
        """OpenCodeATルートを探す"""
        current = self.current_dir
        while current != current.parent:
            if current.name == "OpenCodeAT":
                return current
            current = current.parent
        return None
    
    def update_sota_files(self, version, timestamp, agent_id):
        """SOTA更新時の各階層ファイル更新"""
        sota_info = {
            'local': self.check_local_sota(),
            'parent': self.check_parent_sota(),
            'global': self.check_global_sota(),
            'project': self.check_project_sota()
        }
        
        # Local更新
        if sota_info['local']:
            self.update_local_sota(version, timestamp, agent_id)
        
        # Global更新
        if sota_info['global']:
            self.update_global_sota(version, timestamp, agent_id)
        
        # Project更新
        if sota_info['project']:
            self.update_project_sota(version, timestamp, agent_id)
        
        return sota_info
    
    def update_local_sota(self, version, timestamp, agent_id):
        """Local SOTAファイル更新"""
        sota_file = self.current_dir / "sota_local.txt"
        with open(sota_file, 'w') as f:
            f.write(f'current_best: "{self.performance} GFLOPS"\n')
            f.write(f'achieved_by: "{version}"\n')
            f.write(f'timestamp: "{timestamp}"\n')
            f.write(f'agent_id: "{agent_id}"\n')
    
    def update_global_sota(self, version, timestamp, agent_id):
        """Global SOTAファイル更新"""
        hardware_dir = self.find_hardware_info_dir()
        if hardware_dir:
            sota_file = hardware_dir / "sota_global.txt"
            with open(sota_file, 'w') as f:
                f.write(f'current_best: "{self.performance} GFLOPS"\n')
                f.write(f'achieved_by: "{agent_id}"\n')
                f.write(f'timestamp: "{timestamp}"\n')
                f.write(f'hardware_path: "{self.get_hardware_path()}"\n')
                f.write(f'strategy: "{self.get_strategy()}"\n')
    
    def update_project_sota(self, version, timestamp, agent_id):
        """Project SOTAファイル更新"""
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
        """ハードウェアパスを取得"""
        # プロジェクトルートからの相対パスを算出
        project_root = self.find_project_root()
        if project_root:
            relative_path = self.current_dir.relative_to(project_root)
            return str(relative_path.parent)
        return "unknown"
    
    def get_strategy(self):
        """戦略名を取得"""
        # 現在のディレクトリパスから戦略を推定
        path_parts = self.current_dir.parts
        if len(path_parts) >= 2:
            return path_parts[-2]  # 親ディレクトリ名が戦略名
        return "unknown"

def get_virtual_parent_sota(current_dir):
    """
    Virtual Parent SOTA算出の独立関数
    PG_visible_dir.mdから Virtual parent セクションの📁付きパスを読み込み
    
    例：OpenMP_MPI📁の場合、../MPI📁と../OpenMP📁を参照
    """
    current_path = Path(current_dir)
    
    # PG_visible_dir.mdファイルを探す
    visible_file = current_path / "PG_visible_dir.md"
    if not visible_file.exists():
        return 0.0, None
    
    # Virtual parent パスを抽出
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
            # 親世代ディレクトリ内のPGディレクトリを探索
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

# 使用例
if __name__ == "__main__":
    checker = SOTAChecker("/path/to/PG1.1.1")
    results = checker.check_sota_levels("285.7 GFLOPS")
    
    print("SOTA Levels Updated:")
    for level, updated in results.items():
        if updated:
            print(f"  {level}: NEW SOTA!")
        else:
            print(f"  {level}: no update")