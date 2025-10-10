# Donanım Bilgisi Toplama ve Paylaşım Kılavuzu

## Genel Bakış
Her donanım ortamına ait doğru performans bilgilerini toplayıp tüm aracılar tarafından başvurulabilecek şekilde derleriz.

## Bilgi Toplama Yeri ve Yöntemi

### 1. Toplama konumu hiyerarşisi
```
Flow/TypeII/single-node/
├── hardware_info.md     # ここに集約
├── intel2024/
└── gcc11.3.0/
```

### 2. Toplanacak bilgiler

#### CPU Bilgisi [Önemli: Birden fazla komutla çifte kontrol]
```bash
# Temel bilgiler (birden fazla komutla doğrulayın)
lscpu | grep -E "Model name|CPU\(s\)|Thread|Core|Socket|MHz|cache|Flags"

# /proc/cpuinfo ile de kontrol edin
cat /proc/cpuinfo | grep -E "model name|cpu cores|siblings|cpu MHz|flags" | head -20

# SIMD komut setlerini doğrula
grep -o 'avx[^ ]*\|sse[^ ]*\|fma' /proc/cpuinfo | sort -u

# NUMA bilgisi
numactl --hardware 2>/dev/null || echo "NUMA not available"

# Teorik hesaplama performansı formülü (her hassasiyet için)
# FP64 (double): FLOPS = コア数 × 周波数(GHz) × 2(FMA) × SIMD幅
# FP32 (float):  FLOPS = コア数 × 周波数(GHz) × 2(FMA) × SIMD幅×2
# FP16 (half):   FLOPS = コア数 × 周波数(GHz) × 2(FMA) × SIMD幅×4

# SIMD幅の目安:
# SSE: 2 (FP64), 4 (FP32)
# AVX/AVX2: 4 (FP64), 8 (FP32)
# AVX-512: 8 (FP64), 16 (FP32), 32 (FP16)

# Örnek: Intel Xeon 64 çekirdek × 2.5GHz × 2(FMA) × 8(AVX-512) = 2560 GFLOPS (FP64)
#                                   × 16(AVX-512) = 5120 GFLOPS (FP32)
```

#### Bellek Bilgisi
```bash
# Kapasite ve bant genişliği
lsmem
free -h
cat /proc/meminfo | grep -E "MemTotal|MemAvailable"

# Ayrıntılı bilgiler (root yetkisi gerekebilir)
sudo dmidecode -t memory 2>/dev/null | grep -E "Size|Speed|Type" || echo "dmidecode requires root"

# Teorik bellek bant genişliği hesabı
# バンド幅 = メモリチャネル数 × バス幅(bit)/8 × 周波数(MT/s)
# Örnek: DDR4-3200, 8 kanal
#     8 kanal × 64 bit / 8 × 3200 MT/s = 204.8 GB/s

# STREAM benchmark結果があれば記載
# ない場合は簡易テストを実施推奨
```

#### GPU Bilgisi (varsa)
```bash
# NVIDIA GPU temel bilgileri
nvidia-smi -q | grep -E "Product Name|Memory|Compute|CUDA Cores|Clock"
nvidia-smi --query-gpu=name,memory.total,clocks.sm,clocks.mem --format=csv

# Önemli: Düğüm içindeki GPU sayısını ve bağlantı topolojisini doğrulayın
nvidia-smi topo -m  # GPU’lar arası bağlantı biçimini gösterir (NVLink, PCIe vb.)

# Önemli: CPU-GPU arasındaki NUMA topolojisini doğrulayın
lstopo-no-graphics --of txt  # hwloc ile CPU-GPU NUMA yerleşimini gösterir
numactl --hardware  # NUMA düğümlerini kontrol et
nvidia-smi topo -m | grep CPU  # Her GPU’nun hangi CPU soketine yakın olduğunu kontrol et

# NVLink ayrıntıları
nvidia-smi nvlink -s  # NVLink durumu ve throughput
nvidia-smi nvlink -i 0 -c  # GPU 0 için NVLink sayaçları

# GPU başına ayrıntılar ve MIG yapılandırma kontrolü
nvidia-smi -i 0 -q  # GPU 0 ayrıntıları (MIG etkinliği kontrol edilebilir)

# Toplu iş içinde çalıştırılması önerilen komutlar (10 dk içinde)
# GPU’lar arası bant genişliği ölçümü (p2pBandwidthLatencyTest vb.)
# CUDA_VISIBLE_DEVICES ortam değişkenini kontrol et
echo $CUDA_VISIBLE_DEVICES

# CPU-GPU arası yakınlık/affinity doğrulaması (önemli)
# Örnek: GPU0,1 CPU0’a; GPU2,3 CPU1’e yakınsa
# OpenMP+CUDA’da CPU iş parçalarını uygun NUMA düğümüne yerleştirmek gerekir
export OMP_PROC_BIND=true
export OMP_PLACES=cores
numactl --cpunodebind=0 --membind=0  # GPU0,1 kullanılacaksa
numactl --cpunodebind=1 --membind=1  # GPU2,3 kullanılacaksa

# AMD GPU
rocm-smi --showproductname 2>/dev/null || echo "AMD GPU not detected"
rocm-smi --showtopology 2>/dev/null  # AMD GPU topolojisi

# Teorik hesaplama performansı formülü
# NVIDIA:
#   FP64 = SM数 × FP64コア/SM × 周波数 × 2(FMA)
#   FP32 = SM数 × FP32コア/SM × 周波数 × 2(FMA)
#   FP16 = FP32 × 2 (Tensor Coreなし) または 別途計算 (Tensor Coreあり)

# Örnek:
# V100: 80 SM × 32 FP64/SM × 1.53GHz × 2 = 7.8 TFLOPS (FP64)
#       80 SM × 64 FP32/SM × 1.53GHz × 2 = 15.7 TFLOPS (FP32)
# A100: 108 SM × 32 FP64/SM × 1.41GHz × 2 = 9.7 TFLOPS (FP64)
#       108 SM × 64 FP32/SM × 1.41GHz × 2 = 19.5 TFLOPS (FP32)

# Önemli: Çoklu GPU yapılandırmalarında toplam performansı da belirtin
# Örnek:# 例: 4 GPU × 9.7 TFLOPS = 38.8 TFLOPS (ノード全体のFP64)
```

#### Ağ Bilgisi
```bash
# İnterconnect
ibstat  # InfiniBand
ip link show

# Teorik bant genişliğini belirtin
```

### 3. hardware_info.md formatı

```
# Flow TypeII Single-node Hardware Specifications
Son güncelleme: 2025-07-30 12:00:00 UTC
Toplayan: SE1
Doğrulayan: PG1.1 (imzalı)

## CPU
- Model: Intel Xeon Platinum 8360Y
- Cores: 36 per socket × 2 sockets = 72 cores
- Frequency: 2.4 GHz (base), 3.5 GHz (turbo)
- SIMD: AVX-512
- L3 Cache: 54 MB per socket
- **Teorik hesaplama performansı**: 2764.8 GFLOPS (FP64)
  Formül: 72 çekirdek × 2.4 GHz × 2 (FMA) × 8 (AVX-512)

## Memory
- Capacity: 256 GB (16 GB × 16)
- Type: DDR4-3200
- **Teorik bant genişliği**: 409.6 GB/s
- Ölçülen bant genişliği (STREAM Triad): 380 GB/s

## GPU (TypeII-G için)
- Model: NVIDIA A100 40GB
- **GPU sayısı**: 4 adet/düğüm
- Memory: 40 GB HBM2 (各GPU)
- **GPU’lar arası bağlantı**: NVLink 3.0 (600 GB/s çift yönlü)
- **Topoloji**: Full mesh (tüm GPU’lar NVLink ile doğrudan bağlı)
- **Teorik hesaplama performansı**: 
  - Tekil: 9.7 TFLOPS (FP64), 19.5 TFLOPS (FP32)
  - Düğüm toplamı: 38.8 TFLOPS (FP64), 78.0 TFLOPS (FP32)
- メモリバンド幅: 1.6 TB/s (各GPU)
- **PCIe bağlantısı**: PCIe Gen4 x16 (her GPU-CPU arasında)

## Network
- Type: InfiniBand HDR
- **Teorik bant genişliği**: 200 Gbps
- Gecikme: < 1 μs

## Storage
- Type: Lustre parallel filesystem
- Kapasite: 10 PB (paylaşımlı)
- **Teorik throughput**: 200 GB/s

## Performans Göstergeleri Özeti
- CPU teorik hesaplama performansı: 
  - FP64: 2764.8 GFLOPS (Formül: 72 çekirdek × 2.4 GHz × 2 FMA × 8 AVX-512)
  - FP32: 5529.6 GFLOPS (Formül: 72 çekirdek × 2.4 GHz × 2 FMA × 16 AVX-512)
- Bellek bant genişliği: 
  - Teorik: 409.6 GB/s
  - Ölçülen: 380 GB/s (STREAM Triad)
- B/F oranı: 0.137 Byte/FLOP (bellek sınırlı olabilir)

## Dış kaynaklarla çapraz kontrol
- Intel ARK: https://ark.intel.com/
- NVIDIA Specifications: https://www.nvidia.com/en-us/data-center/
- TOP500 System Details: https://www.top500.org/
- Süper bilgisayarların resmi kılavuzlarıyla çifte kontrol önerilir
```

## Bilgi paylaşımının uygulanışı

### 1. SE aracısının sorumlulukları
- Proje başlangıcında hardware_info.md oluşturun
- **Zorunlu**: Resmi teknik özellikleri web üzerinden çifte kontrol edin
  - İşlemci adıyla Intel ARK veya AMD resmi sitesini kontrol edin
  - GPU adıyla NVIDIA/AMD resmi spesifikasyonlarını kontrol edin
  - Süper bilgisayar adıyla TOP500 ve resmi kılavuzlara bakın
- **Zorunlu**: Her hassasiyet (FP64/FP32/FP16) için teorik performansı formülle birlikte yazın
- Komut çıktıları ve web bilgileri uyuşmazsa ikisini de not düşerek yazın

### 2. PGによるダブルチェック（最低1名）
```bash
# SE → PG（代表者1名以上）
agent_send.sh PG1.1 "[SE] hardware_info.mdを作成しました。Web検索でダブルチェックをお願いします"

# PGがバッチジョブでGPU構成を確認（重要）
cat > check_gpu.sh << 'EOF'
#!/bin/bash
#PJM -L rscgrp=cx-g-small
#PJM -L node=1
#PJM -L elapse=0:10:00
#PJM -j

echo "=== GPU Configuration Check ==="
nvidia-smi
echo ""
echo "=== GPU Topology ==="
nvidia-smi topo -m
echo ""
echo "=== NVLink Status ==="
nvidia-smi nvlink -s
echo ""
echo "=== Available GPUs ==="
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
EOF

pjsub check_gpu.sh

# PGがチェック後、署名を追加
echo "## 検証履歴" >> hardware_info.md
echo "- 2025-07-30 12:30:00 UTC: PG1.1が検証完了。Intel ARKと照合済み" >> hardware_info.md
echo "- 2025-07-30 13:00:00 UTC: PG1.3がGPU構成確認。4GPU全てNVLink接続を確認" >> hardware_info.md
```

### 3. 全エージェントへの通知
```bash
# SE → 全PG
for pg in PG1.1 PG1.2 PG1.3; do
  agent_send.sh $pg "[SE] hardware_info.md検証完了。理論性能比での評価をお願いします"
done

# SE → PM
agent_send.sh PM "[SE] ハードウェア情報収集・検証完了。PG1.1が署名済み"
```

### 3. レポート作成時の活用
```python
# SEのレポート生成コード例
def calculate_efficiency(actual_gflops, hardware_info_path):
    """実効効率を計算"""
    with open(hardware_info_path) as f:
        content = f.read()
        # 理論演算性能を抽出
        import re
        match = re.search(r'理論演算性能.*?(\d+\.?\d*)\s*GFLOPS', content)
        if match:
            theoretical = float(match.group(1))
            efficiency = (actual_gflops / theoretical) * 100
            return f"{actual_gflops} GFLOPS ({efficiency:.1f}% of peak)"
    return f"{actual_gflops} GFLOPS"
```

## 重要な注意事項

1. **理論演算性能の明記は必須**
   - 単なる性能向上だけでなく、理論性能比で評価
   - 「10倍速くなった」より「理論性能の60%達成」が重要

2. **B/F比の考慮**
   - Byte/FLOP比を計算し、メモリ律速かCPU律速か判断

3. **定期的な更新**
   - module loadで環境が変わる場合は再確認
