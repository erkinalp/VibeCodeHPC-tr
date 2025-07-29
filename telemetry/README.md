# OpenCodeAT テレメトリシステム

このディレクトリは、エージェントのメトリクス収集・可視化とOpenTelemetry設定を管理します。

## 📊 機能

### 1. OpenTelemetry監視
- **OTLP (gRPC)** プロトコルでメトリクスとログをエクスポート
- エージェントID、チームID、作業ディレクトリでタグ付け
- Grafana、LangFuse等のバックエンドで可視化

### 2. コンテキスト使用率監視  
- 各エージェントの使用トークン数を追跡（200,000トークン上限）
- Auto-compact発生を検知・記録
- 時系列グラフで可視化

### 3. サブエージェント統計
- `claude -p` の使用状況を分析
- トークン節約効果の定量化

## 🚀 使用方法

### エージェント起動
```bash
# OpenTelemetry自動設定でエージェントを起動
./telemetry/start_agent_with_telemetry.sh PG1.1.1
```

起動時に以下が自動設定されます：
- OpenTelemetry有効化（`otel_config.env.example`から自動生成）
- エージェント識別属性の設定
- サブエージェント統計の有効化

### 設定のカスタマイズ

`otel_config.env`を編集してエンドポイントや認証情報を設定：
```bash
# デフォルトはローカルのOTel Collector
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# LangFuse等の外部サービスを使用する場合
export OTEL_EXPORTER_OTLP_ENDPOINT=https://your-endpoint.com
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your-token"
```

## 📁 ディレクトリ構造

```
telemetry/
├── otel_config.env.example    # OpenTelemetry設定テンプレート  
├── docker-compose.yml         # ローカルテスト環境（Grafana + Prometheus）
├── sub_agent_logs/            # サブエージェント使用ログ
├── context_usage/             # コンテキスト使用率データ
├── auto_compact/              # Auto-compact発生ログ
└── visualization/             # 生成されたグラフ
```

## 🔧 バックエンド設定

### ローカル開発環境
```bash
# Docker ComposeでOTel Collector、Prometheus、Grafanaを起動
docker-compose -f telemetry/docker-compose.yml up -d

# Grafanaにアクセス
# http://localhost:3000 (admin/admin)
```

### 本番環境
- Grafana Cloud
- LangFuse（OpenTelemetryトレーシング対応）
- Datadog、New Relic等のOTLP対応サービス

## 📈 可視化ツール

### コンテキスト使用率
```bash
python telemetry/visualize_context.py
```

### サブエージェント統計
```bash
python telemetry/analyze_sub_agent.py
```

### エージェント健全性監視（SE用）
```bash
python telemetry/monitor_agents.py --se-id SE1
```

## 📚 参考資料

- [Claude Code監視ドキュメント](https://docs.anthropic.com/ja/docs/claude-code/monitoring-usage)
- [OpenTelemetry仕様](https://opentelemetry.io/docs/)