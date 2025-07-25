# OpenCodeAT テレメトリシステム

このディレクトリは、Claude CodeのOpenTelemetryメトリクスを収集・可視化するためのシステムです。

## 📁 ディレクトリ構造

```
telemetry/
├── raw_metrics/      # 生のメトリクスデータ（JSON/CSV形式）
├── context_usage/    # コンテキスト使用率の時系列データ
├── auto_compact/     # auto-compact発生ログ
└── visualization/    # 可視化結果（グラフ画像）
```

## 📊 収集メトリクス

### 1. トークン使用量
- `claude_code.token.usage` - input/output/cacheRead/cacheCreation別
- エージェントID、tmux_paneで識別

### 2. コンテキスト使用率
- 使用トークン数 / 200,000 × 100 (%)
- 各エージェントの時系列推移を記録

### 3. Auto-compact発生
- PreCompactフックで検知
- 発生時刻とエージェントIDを記録

## 🚀 使用方法

### 1. エージェント起動時の設定
```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=console
export OTEL_METRIC_EXPORT_INTERVAL=10000  # 10秒間隔
export OTEL_RESOURCE_ATTRIBUTES="agent_id=SE1,tmux_pane=${TMUX_PANE}"
```

### 2. メトリクス収集
```bash
# コンソール出力をファイルにリダイレクト
claude --dangerously-skip-permissions 2>&1 | tee telemetry/raw_metrics/agent_${AGENT_ID}_$(date +%Y%m%d_%H%M%S).log
```

### 3. 可視化
```bash
python telemetry/visualize_context.py
```

## 📈 出力例

- `visualization/context_usage_timeline.png` - 全エージェントのコンテキスト使用率推移
- `visualization/token_usage_by_agent.png` - エージェント別トークン使用量
- `visualization/auto_compact_events.png` - auto-compact発生頻度

## ⚙️ 設定ファイル

エージェントごとのauto-compactフック設定は、各エージェントの`~/.claude/settings.json`に自動追加されます。