#　📋 OpenCodeAT 設計成果物・ドキュメント一覧

## 核心原則
- changes.md中心設計: 情報の集約化（分散させるのは本当に必要な場合のみ）
- 階層配置の明確化: Agent-shared vs 各エージェント直下

## 必須ドキュメント

### プロジェクトルート直下
```
OpenCodeAT/
├── CLAUDE.md                    # 共通ルール（writer:PM, reader:all）
├── assign_history.txt           # PM管理（writer:PM, reader:all）
├── resource_allocation.md       # リソース割り当て（writer:PM, reader:CI）
├── sota_project.txt             # Project階層SOTA（writer:PG, reader:all）
├── history/
│   └── sota_project_history.txt # Project SOTA履歴（writer:PG, reader:PM）
└── GitHub/                      # CD管理（writer:CD, reader:all）
    ├── changes_public.md        # 統合・匿名化版
    └── repository_name
```

## Agent-shared階層

### Agent-shared/ (全エージェント参照)
```
Agent-shared/
├── directory_map.txt            # エージェント配置（writer:PM, reader:all）
├── budget_history.md            # 予算履歴（writer:PM, reader:CI）
├── changes_unified.md           # 統一changes.mdフォーマット（writer:PM, reader:all）
├── sota_management.md           # SOTA管理システム仕様（writer:PM, reader:all）
├── changes_query/               # changes.md解析ツール群（writer:all）
│   ├── query_changes.py         # SQLライクなchanges.md検索
│   ├── [その他解析コード自由配置]
│   └── README.md                # 使用方法・クエリ例
└── SE-shared/                   # SE専用ツール（writer:SE, reader:SE/PM）
    ├── log_analyzer.py          # ログ解析ツール
    └── performance_trends.png   # 統計グラフ
```

### _remote_info/ (スパコン・ユーザ固有)
```
_remote_info/
├── user_id.txt                  # 秘匿情報（writer:PM, reader:CD）
├── Flow/command.md              # 実行コマンド
└── [スパコン環境設定]
```

### communication/ (通信システム)
```
communication/
├── hpc_agent_send.sh            # メッセージ送信
├── setup_hpc.sh                 # エージェント起動
└── logs/send_log.txt            # 送信履歴
```

## 各エージェント直下

### ハードウェア階層直下
```
Flow/TypeII/single-node/
├── hardware_info.txt           # ハードウェア情報集約（writer:CI, reader:all）
│   ├── CPU: lscpu結果
│   ├── Memory: lsmem結果  
│   ├── Network: 通信バンド幅、レイテンシ
│   ├── Storage: ディスクI/O性能
│   └── Accelerator: GPU/FPGA情報
├── sota_global.txt             # Global階層SOTA（writer:PG, reader:all）
├── intel2024/
└── gcc11.3.0/
```

### CI階層
```
CI1.1/
├── setup.md                    # 環境構築手順
└── job_list_CI1.1.txt          # ジョブ管理
```

### PG階層
```
PG1.1.1/
├── changes.md                   # 【必須】全情報統合（→Agent-shared/changes_unified.md参照）
├── visible_paths.txt            # 参照許可パス一覧（SE管理）
├── sota_local.txt               # Local階層SOTA（writer:PG, reader:all）
└── results/                     # 実行結果ファイル
    ├── job_12345.out
    └── job_12345.err
```

## 情報統合の考え方

### changes.md統合項目（一部）
- code_versions: バージョン履歴
- optimization_notes: 最適化メモ
- performance_data: 性能データ
- sota_candidates: SOTA候補情報

### 分離する理由があるもの
- 実行結果ファイル: サイズが大きい（results/）
- 環境構築手順: CI固有情報（setup.md）
- 予算管理: PM集約必要（budget_history.md）

## 取得・解析方法

### changes.md解析
```bash
# バージョン一覧取得例
grep "^## version:" changes.md | sed 's/## version: //'

# 性能データ抽出例
grep "performance_metric:" changes.md | awk -F'"' '{print $2}'

# SOTA履歴取得例
grep -A1 "sota_level: global" changes.md | grep "current_sota:"
```

### SOTA情報取得
```bash
# Local SOTA確認
cat PG1.1.1/sota_local.txt

# Global SOTA確認  
cat Flow/TypeII/single-node/sota_global.txt

# Project SOTA確認
cat OpenCodeAT/sota_project.txt
```

### 統合クエリ例
```bash
# Agent-shared/changes_query/内の解析ツール活用
python3 Agent-shared/changes_query/query_changes.py --performance-trend
python3 Agent-shared/changes_query/query_changes.py --sota-comparison
```

要点: changes.mdのフォーマットがしっかりしていれば、エージェントが必要に応じて正規表現やPythonでパースして部分的に取得できる。加えて、SOTA情報は専用ファイルで高速アクセス可能。