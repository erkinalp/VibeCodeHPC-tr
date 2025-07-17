# SOTA Management System Design

## SOTA階層管理構造

### **ファイル配置戦略**
```
OpenCodeAT/
├── sota_project.txt              # Project階層SOTA
├── Flow/TypeII/single-node/
│   ├── hardware_info.txt
│   ├── sota_global.txt           # Global階層SOTA
│   └── intel2024/
│       ├── OpenMP_MPI/
│       │   ├── PG1.1.1/
│       │   │   ├── changes.md
│       │   │   └── sota_local.txt    # Local階層SOTA
│       │   └── visible_paths.txt
│       └── OpenMP/
│           └── PG1.1.2/
│               └── sota_local.txt
└── history/
    └── sota_project_history.md     # Project履歴（PMや人間向け）
```

### **各階層の管理方法**

#### **1. Local SOTA (PG直下)**
```python
# PG1.1.1/sota_local.txt
current_best: "285.7 GFLOPS"
achieved_by: "v1.2.1"
timestamp: "2025-07-16 14:30:00 UTC"
agent_id: "PG1.1.1"
```

#### **2. Parent SOTA (Virtual算出)**
```python
# virtual_parent.py - PG1.1.1実行時の例
import os
import glob

def get_virtual_parent_sota():
    """
    ## Current Directory
    OpenMP_MPI📁
    
    ## Relative visible PATH (Read Only)
    
    ### Virtual parent
    ../mpi📁
    ../openmp📁
    
    ### Similar directory  
    ../../gcc📂/openmp_mpi
    """
    
    # visible_paths.txtから取得
    visible_paths = [
        "../mpi",
        "../openmp", 
        "../../gcc/openmp_mpi"
    ]
    
    parent_sota = 0.0
    best_info = None
    
    for path in visible_paths:
        sota_file = os.path.join(path, "*/sota_local.txt")
        for file in glob.glob(sota_file):
            with open(file, 'r') as f:
                perf = float(f.readline().split('"')[1].split()[0])
                if perf > parent_sota:
                    parent_sota = perf
                    best_info = file
    
    return parent_sota, best_info
```

#### **3. Global SOTA (hardware_info.txt階層)**
```python
# Flow/TypeII/single-node/sota_global.txt
current_best: "342.1 GFLOPS"
achieved_by: "PG1.2.4"
timestamp: "2025-07-16 15:00:00 UTC"
hardware_path: "gcc/cuda"
strategy: "CUDA_OpenMP"
```

#### **4. Project SOTA (ルート直下)**
```python
# OpenCodeAT/sota_project.txt
current_best: "450.8 GFLOPS"
achieved_by: "PG2.1.1"
timestamp: "2025-07-16 16:00:00 UTC"
hardware_path: "multi-node/gcc/mpi_openmp"
strategy: "MPI_OpenMP_AVX512"
```

## SOTA判定・更新システム

### **Python実装例**
```python
# sota_checker.py
import os
import json
from pathlib import Path

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
        # visible_paths.txtから取得
        visible_file = self.current_dir / "visible_paths.txt"
        if not visible_file.exists():
            return False
            
        with open(visible_file, 'r') as f:
            visible_paths = [line.strip() for line in f.readlines()]
        
        max_parent_perf = 0.0
        for path in visible_paths:
            full_path = self.current_dir / path
            if full_path.exists():
                for sota_file in full_path.glob("*/sota_local.txt"):
                    with open(sota_file, 'r') as f:
                        perf = float(f.readline().split('"')[1].split()[0])
                        max_parent_perf = max(max_parent_perf, perf)
        
        return self.performance > max_parent_perf
    
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
        """hardware_info.txtが存在するディレクトリを探す"""
        current = self.current_dir
        while current != current.parent:
            if (current / "hardware_info.txt").exists():
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
```

## 利点

### **1. 高速比較**
- **直接読み取り**: 1ファイルで即座に判定
- **changes.md走査不要**: SQLライクな検索が不要

### **2. 堅牢性**
- **専用管理**: SOTA情報の専用ファイル
- **階層別管理**: 各レベルで独立した更新

### **3. 可視性**
- **Global可視**: hardware_info.txt階層で全エージェントから参照可能
- **Project履歴**: PMや人間向けの履歴管理

### **4. 自動化**
- **Virtual Parent**: visible_paths.txtベースの自動算出
- **階層探索**: 自動でのファイル探索と更新

この設計により、効率的で堅牢なSOTA管理システムが実現されます。