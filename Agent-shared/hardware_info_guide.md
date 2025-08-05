# ハードウェア情報収集・共有ガイド

## 概要
各ハードウェア環境の正確な性能情報を収集し、全エージェントが参照できるように集約します。

## 情報収集場所と方法

### 1. 収集場所の階層
```
Flow/TypeII/single-node/
├── hardware_info.md     # ここに集約
├── intel2024/
└── gcc11.3.0/
```

### 2. 収集すべき情報

#### CPU情報
```bash
# 基本情報
lscpu | grep -E "Model name|CPU\(s\)|Thread|Core|Socket|MHz|cache"

# 理論演算性能の計算
# FLOPS = コア数 × 周波数(GHz) × 命令/サイクル × SIMD幅
# 例: 64コア × 2.5GHz × 2(FMA) × 8(AVX-512) = 2560 GFLOPS
```

#### メモリ情報
```bash
# 容量とバンド幅
lsmem
dmidecode -t memory | grep -E "Size|Speed|Type"

# STREAM benchmark結果があれば記載
```

#### GPU情報（該当する場合）
```bash
nvidia-smi -q | grep -E "Product Name|Memory|Compute"

# 理論演算性能
# 例: V100: 7.8 TFLOPS (FP64)
```

#### ネットワーク情報
```bash
# インターコネクト
ibstat  # InfiniBand
ip link show

# 理論バンド幅を記載
```

### 3. hardware_info.mdフォーマット

```
# Flow TypeII Single-node Hardware Specifications
最終更新: 2025-07-30 12:00:00 UTC
収集者: CI1.1

## CPU
- Model: Intel Xeon Platinum 8360Y
- Cores: 36 per socket × 2 sockets = 72 cores
- Frequency: 2.4 GHz (base), 3.5 GHz (turbo)
- SIMD: AVX-512
- L3 Cache: 54 MB per socket
- **理論演算性能**: 2764.8 GFLOPS (FP64)
  計算式: 72 cores × 2.4 GHz × 2 (FMA) × 8 (AVX-512)

## Memory
- Capacity: 256 GB (16 GB × 16)
- Type: DDR4-3200
- **理論バンド幅**: 409.6 GB/s
- 実測バンド幅 (STREAM Triad): 380 GB/s

## GPU (TypeII-Gの場合)
- Model: NVIDIA A100 40GB
- Memory: 40 GB HBM2
- **理論演算性能**: 9.7 TFLOPS (FP64)
- メモリバンド幅: 1.6 TB/s

## Network
- Type: InfiniBand HDR
- **理論バンド幅**: 200 Gbps
- レイテンシ: < 1 μs

## Storage
- Type: Lustre parallel filesystem
- 容量: 10 PB (共有)
- **理論スループット**: 200 GB/s

## 性能指標サマリ
- CPU理論演算性能: 2764.8 GFLOPS
- メモリバンド幅: 380 GB/s (実測)
- B/F比: 0.137 (メモリ律速の可能性)
```

## 情報共有の実装方法

### 1. CIエージェントの責務
- プロジェクト開始時にhardware_info.mdを作成
- Web検索で公式スペックを補完
- 理論演算性能を必ず計算・記載

### 2. 全エージェントへの通知
```bash
# CI → SE
agent_send.sh SE1 "[CI] hardware_info.md作成完了。理論演算性能: 2764.8 GFLOPS"

# SE → 全PG
for pg in PG1.1.1 PG1.1.2 PG1.2.1; do
  agent_send.sh $pg "[SE] hardware_info.mdを参照してください。理論性能比での評価をお願いします"
done

# SE → PM
agent_send.sh PM "[SE] ハードウェア情報収集完了。全エージェントに通知済み"
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