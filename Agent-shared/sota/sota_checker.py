#!/usr/bin/env python3
"""
SOTA Management System - VibeCodeHPC

4 katmanlı SOTA yönetim sistemi (Yerel/Ebeveyn/Küresel/Proje)
"""

import os
import json
from pathlib import Path
import glob

class SOTAChecker:
    def __init__(self, current_dir):
        self.current_dir = Path(current_dir).resolve()  # Mutlak yola dönüştür
        self.performance = None
        
    def check_sota_levels(self, performance_metric):
        """Tüm katmanlarda SOTA değerlendirmesi"""
        self.performance = float(performance_metric.split()[0])
        
        results = {
            'local': self.check_local_sota(),
            'parent': self.check_parent_sota(),
            'hardware': self.check_hardware_sota(),
            'project': self.check_project_sota()
        }
        
        return results
    
    def check_local_sota(self):
        """Yerel SOTA değerlendirmesi"""
        sota_file = self.current_dir / "sota_local.txt"
        if not sota_file.exists():
            return True  # İlk çalıştırmada her zaman SOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def check_parent_sota(self):
        """Ebeveyn SOTA değerlendirmesi (Sanal hesap)"""
        # PG_visible_dir.md dosyasını bul
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
        """Markdown'daki Virtual parent bölümünden 📁 içeren yolları çıkar"""
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
                break  # Bir sonraki bölüme geçince dur
            elif virtual_parent_section and line.startswith("../") and "📁" in line:
                # ../MPI📁 ifadesinden ../MPI'yi çıkar
                path = line.split("📁")[0]
                paths.append(path)
        
        return paths
    
    def check_hardware_sota(self):
        """Donanım SOTA değerlendirmesi"""
        # hardware_info.txt hiyerarşisindeki sota_hardware.txt'yi kontrol et
        hardware_dir = self.find_hardware_info_dir()
        if not hardware_dir:
            return False
            
        sota_file = hardware_dir / "sota_hardware.txt"
        if not sota_file.exists():
            return True  # İlk çalıştırmada her zaman SOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def check_project_sota(self):
        """Proje SOTA değerlendirmesi"""
        # VibeCodeHPC kökündeki sota_project.txt'yi kontrol et
        project_root = self.find_project_root()
        if not project_root:
            return False
            
        sota_file = project_root / "sota_project.txt"
        
        if not sota_file.exists():
            return True  # İlk çalıştırmada her zaman SOTA
            
        with open(sota_file, 'r') as f:
            current_best = float(f.readline().split('"')[1].split()[0])
            
        return self.performance > current_best
    
    def find_hardware_info_dir(self):
        """hardware_info.md dosyasının bulunduğu dizini bul"""
        current = self.current_dir
        while current != current.parent:
            if (current / "hardware_info.md").exists():
                return current
            current = current.parent
        return None
    
    def find_project_root(self):
        """VibeCodeHPC kökünü bul"""
        current = self.current_dir
        while current != current.parent:
            if current.name.startswith("VibeCodeHPC"):
                return current
            current = current.parent
        return None
    
    def update_sota_files(self, version, timestamp, agent_id):
        """SOTA güncellemesinde her katman dosyasını güncelle"""
        sota_info = {
            'local': self.check_local_sota(),
            'parent': self.check_parent_sota(),
            'hardware': self.check_hardware_sota(),
            'project': self.check_project_sota()
        }
        
        if sota_info['local']:
            self.update_local_sota(version, timestamp, agent_id)
        
        if sota_info['hardware']:
            self.update_hardware_sota(version, timestamp, agent_id)
        
        if sota_info['project']:
            self.update_project_sota(version, timestamp, agent_id)
        
        return sota_info
    
    def update_local_sota(self, version, timestamp, agent_id):
        """Yerel SOTA dosyası güncellemesi"""
        sota_file = self.current_dir / "sota_local.txt"
        with open(sota_file, 'w') as f:
            f.write(f'current_best: "{self.performance} GFLOPS"\n')
            f.write(f'achieved_by: "{version}"\n')
            f.write(f'timestamp: "{timestamp}"\n')
            f.write(f'agent_id: "{agent_id}"\n')
    
    def update_hardware_sota(self, version, timestamp, agent_id):
        """Donanım SOTA dosyası güncellemesi"""
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
        """Proje SOTA dosyası güncellemesi"""
        project_root = self.find_project_root()
        if project_root:
            sota_file = project_root / "sota_project.txt"
            with open(sota_file, 'w') as f:
                f.write(f'current_best: "{self.performance} GFLOPS"\n')
                f.write(f'achieved_by: "{agent_id}"\n')
                f.write(f'timestamp: "{timestamp}"\n')
                f.write(f'hardware_path: "{self.get_hardware_path()}"\n')
                f.write(f'strategy: "{self.get_strategy()}"\n')
            
            history_file = project_root / "history" / "sota_project_history.txt"
            history_file.parent.mkdir(exist_ok=True)
            with open(history_file, 'a') as f:
                f.write(f'[{timestamp}] {self.performance} GFLOPS by {agent_id} ({self.get_strategy()})\n')

    def get_hardware_path(self):
        """Donanım yolunu al"""
        project_root = self.find_project_root()
        if project_root:
            relative_path = self.current_dir.relative_to(project_root)
            return str(relative_path.parent)
        return "unknown"
    
    def get_strategy(self):
        """Strateji adını al"""
        path_parts = self.current_dir.parts
        if len(path_parts) >= 2:
            return path_parts[-2]  # Üst dizin adı strateji adıdır
        return "unknown"

def get_virtual_parent_sota(current_dir):
    """
    Virtual Parent SOTA hesaplaması için bağımsız fonksiyon
    PG_visible_dir.md içindeki Virtual parent bölümündeki 📁 içeren yolları okur
    
    Örnek: OpenMP_MPI📁 durumunda, ../MPI📁 ve ../OpenMP📁 referans alınır
    """
    current_path = Path(current_dir)
    
    # PG_visible_dir.md dosyasını bul
    visible_file = current_path / "PG_visible_dir.md"
    if not visible_file.exists():
        return 0.0, None
    
    # Virtual parent yollarını çıkar
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

# CLI実行対応
if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    if len(sys.argv) < 2:
        print("Kullanım:")
        print("  python sota_checker.py <performans> [dizin] [sürüm] [agent_id]")
        print("  Örnek: python sota_checker.py '350.0 GFLOPS'")
        print("  Örnek: python sota_checker.py '350.0 GFLOPS' . v1.2.3 PG1.1")
        sys.exit(1)
    
    performance = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    version = sys.argv[3] if len(sys.argv) > 3 else "unknown"
    agent_id = sys.argv[4] if len(sys.argv) > 4 else "unknown"
    
    checker = SOTAChecker(directory)
    results = checker.check_sota_levels(performance)
    
    print(f"SOTA değerlendirme sonucu ({performance}):")
    for level, is_sota in results.items():
        status = "✓ NEW SOTA!" if is_sota else "- no update"
        print(f"  {level:10s}: {status}")
    
    if any(results.values()):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        checker.update_sota_files(version, timestamp, agent_id)
        print(f"\nSOTA dosyası güncellendi (zaman damgası: {timestamp})")
