# ChangeLog PMオーバーライド例

**注意**: これは`ChangeLog_format_PM_override.md`の作成例です。
PMは実際のプロジェクトに応じてこの例を参考に作成してください。

このドキュメントは基本フォーマット（`ChangeLog_format.md`）への**追加ルールのみ**を定義します。
基本フォーマットの構造は変更できません。

## PMオーバーライド項目

### 1. 性能指標の統一
- **単位の明記**: `test`セクションの`unit`フィールドに必ず記載
  - 行列計算: `GFLOPS` または `MFLOPS`
  - シミュレーション: `iterations/sec` または `seconds`
- **表記精度**: 小数点第1位まで（例: `285.7`）

### 2. request_id形式
```
[PGエージェントID]-[CIエージェントID]-[連番3桁]
例: PG1.2.1-CI1.2-004
```

### 3. プロジェクト固有の必須params
基本フォーマットの`params`セクションに以下を追加：
- `compile_flags`: 使用したコンパイルオプション（必須）
- `mpi_processes`: MPIプロセス数（MPI使用時は必須）
- `omp_threads`: OpenMPスレッド数（OpenMP使用時は必須）

### 4. コンパイル警告の扱い
`compile`の`status: warning`時：
- 並列化に関する警告は`message`に1-2行で要約
- 詳細が必要な場合は`compile_warnings`フィールドを追加（任意）

### 5. SOTA更新時の追加情報
`sota`セクションに以下を任意追加：
- `previous`: 前回の記録値
- `improvement`: 改善率（%表記）

## 記載例（行列計算プロジェクト）

```markdown
### v1.2.3
**変更点**: "OpenMP collapse(2)とMPI領域分割を実装"  
**結果**: 性能向上を確認 `285.7`  
**コメント**: "collapse句により内側ループも並列化、MPIで領域分割を追加"  

<details>

- [x] **compile**
    - status: `warning`
    - request_id: `PG1.1.1-CI1.1-042`
    - message: "OpenMP: 一部のループで並列化が無効化される警告"
    - compile_warnings: "loop at line 45: not vectorized due to data dependency"
    - log: `/results/compile_v1.2.3.log`
- [x] **job**
    - id: `12345`
    - status: `success`
- [x] **test**
    - status: `pass`
    - performance: `285.7`
    - unit: `GFLOPS`
- [x] **sota**
    - scope: `hardware`
    - previous: `241.3`
    - improvement: `+18.4%`
- **params**:
    - nodes: `4`
    - compile_flags: `-O3 -fopenmp -march=native`
    - mpi_processes: `16`
    - omp_threads: `8`

</details>
```

## 差分まとめ

基本フォーマットからの追加点：
1. `test`の`unit`フィールド（基本フォーマットに追加済み）
2. `compile_warnings`フィールド（任意）
3. `sota`の`previous`と`improvement`（任意）
4. `params`の`compile_flags`、`mpi_processes`、`omp_threads`（条件付き必須）

## 注意事項

1. **Markdown構造の保持**
   - `<details>`タグは絶対に変更しない
   - フィールドの階層構造を維持
   - 日本語での記述を継続

2. **Python解析との互換性**
   - フィールド名は半角英数字とアンダースコアのみ
   - 数値は引用符なしで記載可能
   - 単位は別フィールドに分離

3. **運用ルール**
   - PMはプロジェクト開始時にこの例を参考に作成
   - 途中変更は最小限に
   - 全エージェントへの周知を徹底