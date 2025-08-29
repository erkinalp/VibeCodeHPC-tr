#　📋 VibeCodeHPC 設計成果物・ドキュメント一覧

## 核心原則
- ChangeLog.md中心設計: 情報の集約化（分散させるのは本当に必要な場合のみ）
- 階層配置の明確化: Agent-shared vs 各エージェント直下

## 必須ドキュメント

### プロジェクトルート直下
```
VibeCodeHPC/
├── CLAUDE.md                    # 共通ルール（writer:PM, reader:all）
├── assign_history.txt           # PM管理（writer:PM, reader:all）
├── resource_allocation.md       # リソース割り当て（writer:PM, reader:all）
├── sota_project.txt             # Project階層SOTA（writer:PG, reader:all）
├── history/
│   └── sota_project_history.txt # Project SOTA履歴（writer:PG, reader:PM）
├── GitHub/                      # CD管理（writer:CD, reader:all）
│   ├── changelog_public.md      # 統合・匿名化版
│   └── repository_name
└── User-shared/                 # ユーザ向け成果物（writer:SE/PM, reader:User）
    ├── final_report.md          # 最終報告書
    ├── reports/                 # 統合レポート
    └── visualizations/          # グラフ・図表
```

## Agent-shared階層

### Agent-shared/ (全エージェント参照)
```
Agent-shared/
├── change_log/                  # ChangeLog関連ファイル
│   ├── ChangeLog_format.md      # 基本フォーマット定義（writer:PM, reader:all）
│   ├── ChangeLog_format_PM_override_template.md # PMオーバーライドテンプレート（writer:運営, reader:PM）
│   ├── changelog_analysis_template.py # 解析テンプレート（writer:SE, reader:all）
│   └── changelog_helper.py      # ChangeLog記録ヘルパー（writer:all, reader:all）
├── budget/                      # 予算管理関連
│   ├── budget_history.md        # 予算履歴（writer:PM, reader:all）
│   ├── budget_history_template.md # 予算履歴テンプレート（writer:運営, reader:PM）
│   ├── budget_termination_criteria.md # 予算ベース終了条件（writer:PM, reader:all）
│   └── budget_visualizer_example.py # 予算可視化例（writer:SE, reader:all）
├── sota/                        # SOTA管理・可視化
│   ├── sota_management.md       # SOTA管理システム仕様（writer:PM, reader:all）
│   ├── sota_checker.py          # SOTA確認スクリプト（writer:SE, reader:all）
│   ├── sota_visualizer.py       # SOTA可視化ツール（writer:SE, reader:all）
│   ├── sota_visualizer_usage.md # 可視化ツール使用法（writer:SE, reader:all）
│   └── sota_grouping_config_template.yaml # グループ設定テンプレート（writer:PM, reader:SE）
├── strategies/                  # 最適化戦略
│   └── auto_tuning/
│       ├── typical_hpc_code.md  # HPC最適化の典型例（writer:PM, reader:all）
│       └── evolutional_flat_dir.md # 進化的探索戦略（writer:PM, reader:all）
├── directory_pane_map_example.md # エージェント配置例（writer:運営, reader:PM）
├── hardware_info_guide.md       # ハードウェア情報収集ガイド（writer:SE, reader:all）
├── compile_warning_workflow.md  # コンパイル警告処理フロー（writer:SE, reader:PG）
├── ssh_sftp_guide.md            # SSH/SFTP接続・実行ガイド（writer:PM, reader:PG/SE）
├── sub_agent_usage.md           # サブエージェント使用法（writer:PM, reader:all）
├── multi_agent_comparison.md    # マルチエージェント比較（writer:運営, reader:PM）
├── report_hierarchy.md          # レポート階層構成（writer:SE, reader:all）
├── PG_visible_dir_format.md     # PG可視化ディレクトリ形式（writer:SE, reader:PG）
├── artifacts_position.md        # 成果物配置ルール（本ファイル）
└── log_analyzer.py              # ログ解析スクリプト（writer:SE, reader:all）
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
├── hardware_info.md            # ハードウェア情報集約（writer:SE/PG, reader:all）
│   ├── CPU: lscpu結果
│   ├── Memory: lsmem結果  
│   ├── Network: 通信バンド幅、レイテンシ
│   ├── Storage: ディスクI/O性能
│   └── Accelerator: GPU/FPGA情報
├── sota_hardware.txt           # Hardware階層SOTA（writer:PG, reader:all）
├── intel2024/                  # コンパイラ環境階層
│   └── setup.md                # 環境構築手順（writer:最初のPG, reader:all PGs）
└── gcc11.3.0/                  # コンパイラ環境階層
    └── setup.md                # 環境構築手順（writer:最初のPG, reader:all PGs）
```

### PG階層
```
PG1.1.1/
├── ChangeLog.md                 # 【必須】全情報統合（→Agent-shared/change_log/ChangeLog_format.md参照）
├── visible_paths.txt            # 参照許可パス一覧（SE管理）
├── sota_local.txt               # Local階層SOTA（writer:PG, reader:all）
└── results/                     # 実行結果ファイル
    ├── job_12345.out
    └── job_12345.err
```

## 情報統合の考え方

### ChangeLog.md統合項目（一部）
- code_versions: バージョン履歴
- optimization_notes: 最適化メモ
- performance_data: 性能データ
- sota_candidates: SOTA候補情報

### 分離する理由があるもの
- 実行結果ファイル: サイズが大きい（results/）
- 環境構築手順: コンパイラ環境階層で共有（intel2024/setup.md等）
- 予算管理: PM集約必要（budget_history.md）

## 取得・解析方法

### ChangeLog.md解析
```bash
# バージョン一覧取得例
grep "^### v" ChangeLog.md | sed 's/### //'

# 性能データ抽出例
grep "performance:" ChangeLog.md | grep -o '`[^`]*`' | tr -d '`'

# SOTA履歴取得例
grep -A1 "\*\*sota\*\*" ChangeLog.md | grep "scope: \`project\`"
```

### SOTA情報取得
```bash
# Local SOTA確認
cat PG1.1.1/sota_local.txt

# Hardware SOTA確認  
cat Flow/TypeII/single-node/sota_hardware.txt

# Project SOTA確認
cat VibeCodeHPC/sota_project.txt
```

### 統合クエリ例
```bash
# Agent-shared/内の解析ツール活用例
# Python実行: python3を使用

## ChangeLog記録（PG用）
python3 Agent-shared/change_log/changelog_helper.py -v 1.0.0 -c "OpenMP並列化実装" -m "初回実装"

## SOTA可視化（SE用）  
python3 Agent-shared/sota/sota_visualizer.py --level project
python3 Agent-shared/sota/sota_visualizer.py --level family

## ChangeLog解析（SE用）
python3 Agent-shared/change_log/changelog_analysis_template.py
```

要点: ChangeLog.mdのフォーマットがしっかりしていれば、エージェントが必要に応じて正規表現やPythonでパースして部分的に取得できる。加えて、SOTA情報は専用ファイルで高速アクセス可能。