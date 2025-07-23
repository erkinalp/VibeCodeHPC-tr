# Changes Log Format - Unified for HPC Multi-Agent System

## Overview
統合された changes.md フォーマット：シンプルさと機能性のバランスを重視し、エージェント間連携と自動解析を両立。

## Unified Format Template

```markdown
## version: v1.2.3 (PG writes)
change_summary: "OpenMP collapse(2)とMPI領域分割を追加"
timestamp: "2025-07-16 12:34:56 UTC"
code_files: "mat-mat-noopt_v1.2.3.c"

# Build & Execution (CI updates)
compile_status: success | fail | pending
job_id: "87654321"
job_status: pending | running | completed | failed | timeout
test_status: pass | fail | partial | skip
performance_metric: "285.7 GFLOPS"
execution_time: "315.2 seconds"
compute_cost: "12.5 node-hours"

# Analysis & Planning (PG updates)
sota_level: local | parent | global | project
current_sota: "285.7 GFLOPS"
technical_comment: "collapse(2)で15%向上、MPI分割でさらに20%向上"
next_steps: "次回はAVX512ベクトル化を試行"
lessons_learned: "ハイブリッド並列はMPI 4プロセス以上で収穫逓減"
error_analysis: "なし"
```

## Core Principles

### **1. 必須項目（Mandatory Fields）**
- **version**: バージョン番号
- **change_summary**: 変更概要（日本語）
- **timestamp**: タイムスタンプ
- **compile_status**: コンパイル状況
- **test_status**: テスト結果
- **performance_metric**: 性能指標

### **2. 簡素化された項目（Simplified Fields）**
- **code_files**: ファイル名（複数対応）
- **sota_updated**: SOTA更新の有無（true/false）
- **compute_cost**: 計算コスト

### **3. 日本語化項目（Japanese Fields）**
- **change_summary**: 変更概要
- **technical_comment**: 技術的コメント
- **next_steps**: 次のステップ
- **lessons_learned**: 学んだこと
- **error_analysis**: エラー分析


## Field Specifications

### **Status Values**
- **compile_status**: success, fail, pending
- **job_status**: pending, running, completed, failed, timeout
- **test_status**: pass, fail, partial, skip
- **sota_level**: local, parent, global, project

### **SOTA Level Definitions**
- **local**: PG視点でのSOTA更新（自身のディレクトリ内）
- **parent**: 継承元の📁全体でのSOTA更新（例：intel2024📂全体）
- **global**: 指定されたハードウェア全体でのSOTA更新（例：single-node全体）
- **project**: プロジェクト全体でのSOTA更新（全ハードウェア・戦略を含む）

### **Required Format**
- **version**: v[major].[minor].[patch] (e.g., v1.2.3)
- **timestamp**: YYYY-MM-DD HH:MM:SS UTC
- **performance_metric**: [number] [unit] (e.g., 285.7 GFLOPS)
- **compute_cost**: [number] node-hours

### **File Naming Convention**
- **Base rule**: makefileの修正はせず、ファイルは上書きせず手元に実行ファイル名_v0.0.0.cのように
- **Version management**: コピーを作成してからファイルを上書きしていくバージョン管理を推奨

### **Version Management Strategy**
#### **Major Version (v1.0.0)**
- APIの変更に互換性のない場合、一つ以上の破壊的な変更を含む場合
- 根本から設計を見直すレベルのリファクタリング時
- 異なる最適化戦略のブランチを複数保持したい時

#### **Minor Version (v0.1.0)**
- 後方互換性があり機能性を追加した場合
- 並列化実装に変更を加えた場合

#### **Patch Version (v0.0.1)**
- 後方互換性を伴うバグ修正

## Usage Guidelines

### **For PG (Program Generator)**
1. **即座更新**: コード生成後すぐに基本情報を記録
2. **段階的更新**: コンパイル→実行→分析の各段階で更新
3. **末尾追加**: 新しいバージョンは必ずファイル末尾に追加（chronological order）
4. **依存関係**: visible_paths.txtを参照して dependencies を記録

### **File Management Rules**
- **追加方式**: 新しいエントリは常にファイル末尾に追加
- **ソート不要**: バージョン番号でのソートは不要（時系列順が自然）
- **上書き禁止**: 既存エントリの編集は避ける（CIが状態更新する場合を除く）

### **For CI (Continuous Integration)**
1. **状態更新**: compile_status, job_status の更新
2. **ファイル記録**: 実行結果ファイルのパス記録
3. **完了通知**: agent_send.sh でPGに完了を通知

### **For SE (System Engineer)**
1. **監視**: 複数PGのchanges.mdを監視
2. **統計**: performance_metric や compute_cost の分析
3. **調整**: dependencies の最適化提案

### **For PM (Project Manager)**
1. **予算管理**: compute_cost の集約とestimated_remaining_budget の更新
2. **SOTA承認**: sota_level=global の承認
3. **リソース調整**: performance/cost 比に基づく再配分

## Validation Rules

1. **必須項目チェック**: version, agent_id, timestamp, change_summary
2. **状態整合性**: compile_status=success → job実行可能
3. **時系列整合性**: timestamp < compile_time < job実行時間
4. **予算制約**: compute_cost ≤ estimated_remaining_budget
5. **依存関係**: dependencies内のパスが visible_paths.txt に存在

## Real-World Example (複数バージョン例)

```markdown
## version: v1.0.0
change_summary: "ベースラインコード"
timestamp: "2025-07-16 10:00:00 UTC"
code_files: "mat-mat-noopt_v1.0.0.c"
compile_status: "success"
job_id: "12345"
job_status: "completed"
test_status: "pass"
performance_metric: "50.5 GFLOPS"
execution_time: "800.2 seconds"
sota_updated: true
compute_cost: "8.0 node-hours"
technical_comment: "オリジナルコードのベースライン性能"
next_steps: "OpenMP並列化を実装"
lessons_learned: "シングルスレッドでの基本性能を確認"
error_analysis: "なし"

## version: v1.1.0
change_summary: "外側ループにOpenMP並列化を追加"
timestamp: "2025-07-16 11:30:00 UTC"
code_files: "mat-mat-noopt_v1.1.0.c"
compile_status: "success"
job_id: "12350"
job_status: "completed"
test_status: "pass"
performance_metric: "180.2 GFLOPS"
execution_time: "225.1 seconds"
sota_updated: true
compute_cost: "10.5 node-hours"
technical_comment: "OpenMP並列化で約3.6倍の性能向上"
next_steps: "collapse(2)で更なる最適化"
lessons_learned: "40スレッドでスケーラビリティ良好"
error_analysis: "なし"

```

## Query Examples

### **バージョン一覧取得**
```bash
grep "^## version:" changes.md | sed 's/## version: //'
```

### **SOTA履歴取得**
```bash
grep -A10 "sota_updated: true" changes.md | grep "performance_metric:" | awk -F'"' '{print $2}'
```

### **予算使用量集計**
```bash
grep "compute_cost:" changes.md | awk -F'"' '{sum+=$2} END {print sum " node-hours"}'
```

### **エラー分析**
```bash
grep -A15 "compile_status: \"fail\"" changes.md | grep -E "(error_analysis|technical_comment):"
```

### **性能推移グラフ用データ**
```bash
grep -E "^## version:|performance_metric:" changes.md | paste - - | awk -F'\t' '{print $1 "\t" $2}'
```

## Migration Guide

### **From changes.md (日本語版)**
- ファイル名 → code_filename
- 何をしたか → change_summary
- compile → compile_status
- 実行性能 → performance_metric
- 結果を見てコメント → technical_comment

### **From changes_template.md**
- comment → technical_comment
- sota → sota_level
- 追加: agent_id, dependencies, compute_cost

### **From changes_example.md**
- 削除: memory_usage, cpu_utilization, log_entry_id
- 簡素化: resource_efficiency → compute_cost
- 日本語化: technical_comment, next_steps, lessons_learned

この統合フォーマットにより、シンプルさと機能性を両立したchanges.md管理が実現されます。