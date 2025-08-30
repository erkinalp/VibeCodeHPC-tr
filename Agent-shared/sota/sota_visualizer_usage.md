# SOTA Visualizer 使用ガイド

## 概要
`sota_visualizer.py`は、VibeCodeHPCプロジェクトの4階層SOTA（State-of-the-Art）性能推移を可視化するツールです。

## SOTA階層の定義

### 4つの階層
1. **Local**: 各PGエージェント内での最高性能
   - グラフ数 = PGエージェントの累計数
   - 例: PG1.1.1, PG1.1.2, PG2.1.1...

2. **Family**: 同一ミドルウェア階層（第2世代以降）での最高性能
   - グラフ数 = 使用した技術の組み合わせ数
   - 例: OpenMP, MPI, OpenMP_MPI, CUDA...

3. **Hardware**: ハードウェア構成全体での最高性能
   - グラフ数 = ハードウェア構成ディレクトリ数（≈ SEの累積数）
   - 例: single-node/intel2024, multi-node/gcc...

4. **Project**: プロジェクト全体での最高性能
   - グラフ数 = 1（全体を統合）

## 基本的な使い方

```bash
# プロジェクト全体のSOTA推移（デフォルト）
python Agent-shared/sota/sota_visualizer.py

# 特定階層のSOTA推移
python Agent-shared/sota/sota_visualizer.py --level local    # PGごと
python Agent-shared/sota/sota_visualizer.py --level family   # ミドルウェアごと
python Agent-shared/sota/sota_visualizer.py --level hardware # ハードウェアごと

# 全階層のグラフを一括生成
python Agent-shared/sota/sota_visualizer.py --level all
```

## オプション

### X軸の選択
```bash
# 経過時間ベース（デフォルト）
python Agent-shared/sota/sota_visualizer.py --x-axis time

# 更新回数ベース
python Agent-shared/sota/sota_visualizer.py --x-axis count
```

### Y軸スケール
```bash
# リニアスケール（デフォルト）
python Agent-shared/sota/sota_visualizer.py

# 対数スケール（性能差が大きい場合に有効）
python Agent-shared/sota/sota_visualizer.py --log-scale
```

### 理論性能の表示
```bash
# 理論性能を表示（デフォルト）
python Agent-shared/sota/sota_visualizer.py

# 理論性能を非表示
python Agent-shared/sota/sota_visualizer.py --no-theoretical

# 理論性能が不明な場合の上限設定（最高性能の10%上をデフォルト）
python Agent-shared/sota/sota_visualizer.py --theoretical-ratio 0.2  # 20%上に設定
```

### デバッグ機能
```bash
# サマリー表示（グラフ生成なし、データ確認のみ）
python Agent-shared/sota/sota_visualizer.py --summary

# 出力例:
# [PROJECT]
#   全体: 
#     (120.5m, 234.5 GFLOPS)
#     (145.2m, 256.7 GFLOPS)
#     ... and 23 more points
# [TICK CHECK]
#   Max time: 17.3 hours
#   Estimated ticks: 1038
#   ⚠️ WARNING: Would exceed MAXTICKS limit!
#   ✅ Fix applied: MaxNLocator(nbins=15)

# Efficient版も同様のサマリー機能を提供
python Agent-shared/sota/sota_visualizer_efficient.py --summary
```

## 出力先（v2での改善）
- 生成されたグラフ: `/User-shared/visualizations/sota/[階層]/`
  - `/sota/project/` - プロジェクト全体
  - `/sota/hardware/` - ハードウェア構成ごと
  - `/sota/family/` - ミドルウェア階層ごと
  - `/sota/local/` - PGエージェントごと
  - `/sota/comparison/` - 比較グラフ
- レポート: `/User-shared/reports/sota_visualization_report.md`

## ChangeLog.mdの読み取りロジック

### 対応フォーマット
```markdown
### v1.0.0
**生成時刻**: `2025-01-30T12:00:00Z`  
**結果**: 理論性能の65.1%達成 `312.4 GFLOPS`

または

- performance: `312.4`
- unit: `GFLOPS`
```

### 単位の自動変換
- **TFLOPS → GFLOPS**: 自動的に1000倍して統一
- **実行時間 → スループット**: ms/secの場合は逆数を取って性能指標に変換
- **その他の単位**: GB/s, fps などもそのまま使用可能

### SOTA判定
- 各階層で**単調増加**のグラフを生成（性能が向上した時のみプロット）
- 階段状のグラフで視覚的にSOTA更新タイミングを表現

## ルーフラインモデル的表示

### 理論性能の取得
1. `hardware_info.md`から自動読み取り
2. 見つからない場合は最高性能の指定割合上に設定
3. 赤い破線で理論上限を表示

### 注意事項
- 理論性能に到達するとは限らない
- 初期段階では最高性能の10%上をデフォルト上限とする
- `--theoretical-ratio`で調整可能

## SEエージェントでの活用例

```python
# SEのChangeLog監視スクリプト内で
import subprocess
from pathlib import Path

# 定期的に全階層のグラフを更新
def update_sota_graphs():
    script_path = Path("Agent-shared/sota/sota_visualizer.py")
    
    # 全階層を一括生成
    subprocess.run(["python", str(script_path), "--level", "all"])
    
    # 特に重要なプロジェクト全体は追加オプションで生成
    subprocess.run(["python", str(script_path), 
                   "--level", "project", 
                   "--log-scale"])  # 対数版も生成
    
    print("✅ SOTA graphs updated")

# 5分ごとに実行
update_sota_graphs()
```

## トラブルシューティング

### グラフが生成されない
- ChangeLog.mdが正しいフォーマットか確認
- 生成時刻（UTC）が記録されているか確認
- 結果に数値と単位が含まれているか確認

### 理論性能が表示されない
- hardware_info.mdに「理論性能」が記載されているか確認
- `--theoretical-ratio`で手動設定も可能

### 性能が正しく比較できない
- 単位が統一されているか確認（GFLOPS推奨）
- 実行時間の場合は自動的に逆数変換される