# SOTA Yönetim Sistemi Tasarımı

## SOTA Katman Yönetim Yapısı

### **Dosya Yerleşim Stratejisi**
```
VibeCodeHPC/
├── sota_project.txt              # Project katmanı SOTA
├── Flow/TypeII/single-node/
│   ├── hardware_info.md
│   ├── sota_hardware.txt         # Hardware katmanı SOTA
│   └── intel2024/
│       ├── OpenMP_MPI/
│       │   ├── PG1.1.1/
│       │   │   ├── ChangeLog.md
│       │   │   └── sota_local.txt    # Local katmanı SOTA
│       │   └── visible_paths.txt
│       └── OpenMP/
│           └── PG1.1.2/
│               └── sota_local.txt
└── history/
    └── sota_project_history.md     # Project geçmişi (PM ve insan için)
```

### **Her Katmanın Yönetim Yöntemi**

#### **1. Local SOTA (PG dizini altında)**
```python
# PG1.1.1/sota_local.txt
current_best: "285.7 GFLOPS"
achieved_by: "v1.2.1"
timestamp: "2025-07-16 14:30:00 UTC"
agent_id: "PG1.1.1"
```

#### **2. Family SOTA (aynı ara katman yazılımı içinde üst-alt nesil)**
PG_visible_dir.md'den evrimsel hiyerarşinin üst nesilini referans alarak hesaplanır. Örnek: OpenMP_MPI ise, aynı derleyici altındaki MPI ve OpenMP üst nesildir.

#### **3. Hardware SOTA (hardware_info.md katmanı)**
```python
# Flow/TypeII/single-node/sota_hardware.txt
current_best: "342.1 GFLOPS"
achieved_by: "PG1.2.4"
timestamp: "2025-07-16 15:00:00 UTC"
hardware_path: "gcc/cuda"
strategy: "CUDA_OpenMP"
```

#### **4. Project SOTA (kök dizin altında)**
```python
# VibeCodeHPC/sota_project.txt
current_best: "450.8 GFLOPS"
achieved_by: "PG2.1.1"
timestamp: "2025-07-16 16:00:00 UTC"
hardware_path: "multi-node/gcc/mpi_openmp"
strategy: "MPI_OpenMP_AVX512"
```

## SOTA Değerlendirme ve Güncelleme Sistemi

### **Python Uygulaması**
Uygulama `Agent-shared/sota/sota_checker.py` dosyasına ayrılmıştır

### **Temel Kullanım Yöntemi**
```python
from Agent-shared.sota_checker import SOTAChecker

# PG aracısı içinde kullanım örneği
checker = SOTAChecker(os.getcwd())  # Mevcut PG dizini
results = checker.check_sota_levels("285.7 GFLOPS")

# Standart çıktıda sonuç doğrulama
print("SOTA Levels Updated:")
for level, updated in results.items():
    if updated:
        print(f"  {level}: NEW SOTA!")
    else:
        print(f"  {level}: no update")

# SOTA güncellemesinde dosya güncelleme
if any(results.values()):
    checker.update_sota_files(version="v1.2.3", 
                             timestamp="2025-07-16 14:30:00 UTC",
                             agent_id="PG1.1.1")
```

## Avantajlar

### **1. Hızlı Karşılaştırma**
- **Doğrudan okuma**: 1 dosya ile anında değerlendirme
- **ChangeLog.md taraması gereksiz**: SQL benzeri arama gereksiz

### **2. Sağlamlık**
- **Özel yönetim**: SOTA bilgisi için özel dosya
- **Katman bazlı yönetim**: Her seviyede bağımsız güncelleme

### **3. Görünürlük**
- **Hardware görünürlüğü**: hardware_info.md katmanında tüm aracılardan başvurulabilir
- **Project geçmişi**: PM ve insan için geçmiş yönetimi

### **4. Otomasyon**
- **Family SOTA**: visible_paths.txt tabanlı otomatik hesaplama
- **Katman keşfi**: Otomatik dosya keşfi ve güncelleme

Bu tasarım sayesinde verimli ve sağlam bir SOTA yönetim sistemi gerçekleştirilir.

