# OpenCodeAT v0.3.2 重要な問題と対策

## 1. PM起動の責任分担が不明確

### 現状の問題
- PM起動に複数の手順が必要（hooks設定 → telemetry起動）
- start_agent.shは空のペイン専用で、PM自身には使えない
- ユーザが手動でコマンドを実行する必要がある

### 責任の明確化
| タスク | 責任者 | 理由 |
|--------|--------|------|
| tmuxセッション作成 | setup.sh | 自動化済み |
| PM用hooks設定 | **ユーザ** | PM起動前に必要 |
| PM起動 | **ユーザ** | MCPサーバ設定後 |
| 他エージェント起動 | **PM** | start_agent.sh使用 |
| プロジェクト開始時刻記録 | **SessionStart hook** | PM初回起動時 |

### 改善案
```bash
# PM起動を1コマンドに統合する新スクリプト
./start_pm.sh
```

## 2. プロジェクト開始時刻が記録されない

### 原因
SessionStart hookが正しく動作するには：
1. hooks設定が完了している
2. agent_and_pane_id_table.jsonlにPMのエントリがある
3. TMUX_PANE環境変数が正しい

### 現在の問題
- PMのhooks設定前に起動すると、SessionStart hookが動作しない
- project_start_time.txtが作成されない

## 3. トークン数可視化が自動実行されない

### 原因
context_usage_monitor.pyは手動実行が必要：
```bash
python telemetry/context_usage_monitor.py
```

### 改善案
- SEエージェントが定期的に実行
- またはcronジョブで自動化

## 推奨される解決策

### 1. PM起動スクリプトの作成
`start_pm.sh`を作成して、以下を自動化：
1. PM用のhooks設定
2. telemetry起動
3. 初期化メッセージの表示

### 2. プロジェクト初期化の改善
- PMの初期化時に明示的にproject_start_time.txtを作成
- SessionStart hookに依存しない方法を検討

### 3. 可視化の自動化
- SEのタスクにcontext_usage_monitor.py実行を追加
- またはPMが定期的に実行を指示