# OpenCodeAT Claude Code Hooks 配置ガイド（PM向け）

## 概要
Claude Code hooksは、エージェントの挙動を制御する仕組みです。特に：
- **ポーリング型エージェント（PM, SE, CI, CD）**: 待機状態を防ぎ、常にアクティブに保つ
- **イベント駆動型エージェント（PG, ID）**: 通常通り待機を許可
- **全エージェント**: auto-compact後の必須ファイル再読み込みを促す

## 自動配置（推奨）

### start_agent.shを使用した配置
```bash
# デフォルト（hooksとtelemetry両方有効）
./communication/start_agent.sh PG1.1.1 /Flow/TypeII/single-node/intel2024/OpenMP

# hooksのみ無効化
OPENCODEAT_ENABLE_HOOKS=false ./communication/start_agent.sh PG1.1.1 /path/to/dir

# telemetryのみ無効化
OPENCODEAT_ENABLE_TELEMETRY=false ./communication/start_agent.sh PG1.1.1 /path/to/dir

# 両方無効化（軽量モード）
OPENCODEAT_ENABLE_HOOKS=false OPENCODEAT_ENABLE_TELEMETRY=false ./communication/start_agent.sh PG1.1.1 /path/to/dir
```

## 手動配置（トラブルシューティング用）

### 1. 個別エージェントへの配置
```bash
# エージェントタイプを確認
# PM, SE, CI, CD → polling
# PG, ID → event-driven

# hooksを配置
./Agent-shared/setup_agent_hooks.sh SE1 /path/to/SE1/workdir polling
./Agent-shared/setup_agent_hooks.sh PG1.1.1 /path/to/PG1.1.1/workdir event-driven
```

### 2. 配置されるファイル
各エージェントの作業ディレクトリに以下が配置されます：
```
{AGENT_DIR}/
└── .claude/
    ├── hooks/
    │   ├── session_start.py  # セッション開始時の処理
    │   └── stop.py          # 待機時の処理（タイプ別）
    └── settings.local.json  # hooks有効化設定
```

## エージェントタイプ別の挙動

### ポーリング型（PM, SE, CI, CD）
- **Stop hook**: 待機を阻止し、定期タスクリストを提示
- **SessionStart hook**: auto-compact検知と必須ファイルリスト提示
- **推奨巡回間隔**:
  - PM: 2-5分（全体監視）
  - SE: 3-10分（進捗監視、ジョブ時間に応じて調整）
  - CI: 常時（非同期対応）
  - CD: 非同期（GitHub同期）

### イベント駆動型（PG, ID）
- **Stop hook**: 通常通り待機を許可
- **SessionStart hook**: auto-compact検知と必須ファイルリスト提示

## session_idの追跡

### agent_and_pane_id_table.jsonlの更新
Claude起動後、SessionStart hookが自動的に：
1. session_idを記録
2. エージェントのステータスを"running"に更新
3. 作業ディレクトリ（cwd）を記録

```jsonl
{"agent_id": "PG1.1.1", "tmux_session": "Team1_Workers1", "tmux_window": 0, "tmux_pane": 3, "claude_session_id": "abc123...", "status": "running", "cwd": "/OpenCodeAT-jp/Flow/...", "last_updated": "2025-08-02T12:34:56Z"}
```

## トラブルシューティング

### hooks が動作しない場合
1. `.claude/hooks/` ディレクトリの存在確認
2. Pythonスクリプトの実行権限確認
3. `settings.local.json`のhooks有効化確認
4. uvコマンドの利用可能性確認

### エージェントが頻繁に停止する場合
1. stop hookの`stop_hook_active`チェックが正常か確認
2. エージェントタイプの判定が正しいか確認
3. 必要に応じて`OPENCODEAT_ENABLE_HOOKS=false`で一時無効化

### session_idが記録されない場合
1. `TMUX_PANE`環境変数の存在確認
2. agent_and_pane_id_table.jsonlの書き込み権限確認
3. tmuxペイン番号とテーブルの整合性確認

## 注意事項

1. **hook配置タイミング**: Claude起動前に配置する必要があります
2. **既存hooks**: 既にhooksがある場合は上書きされます
3. **プロジェクト固有設定**: 各エージェントは独立したhooks設定を持ちます
4. **auto-compact対策**: コンテキスト使用率95%付近では特に重要

## 高度な設定

### カスタムhooksの追加
`Agent-shared/hooks_template/`にカスタムhookを追加して、setup_agent_hooks.shを修正することで、プロジェクト固有のhooksを配置できます。

### hooks無効化の使い分け
- **開発/デバッグ時**: `OPENCODEAT_ENABLE_HOOKS=false`
- **本番運用時**: hooks有効（デフォルト）
- **リソース制約時**: telemetryとhooks両方無効化

## 参考資料
- Claude Code hooks公式ドキュメント
- `Agent-shared/hooks_template/` 内の各スクリプト
- `telemetry/README.md`（telemetryとの連携）