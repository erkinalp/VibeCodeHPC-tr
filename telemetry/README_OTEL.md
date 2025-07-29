# OpenCodeAT OpenTelemetry設定ガイド

## 概要

このドキュメントは、OpenCodeATプロジェクトにおけるOpenTelemetry設定について説明します。
Issue #10と#12の解決として、consoleからOTLPへの移行とエージェント別監視を実装しています。

## 🚀 クイックスタート

エージェント起動時に自動的にOpenTelemetryが有効化されます：

```bash
# エージェントを起動（例：PG1.1.1）
./telemetry/start_agent_with_telemetry.sh PG1.1.1
```

## 📊 設定ファイル

### otel_config.env.example

基本的なOpenTelemetry設定のテンプレートです。初回起動時に自動的に`otel_config.env`にコピーされます：

- **エクスポーター**: `otlp`（consoleから変更）
- **プロトコル**: `grpc`
- **エンドポイント**: `http://localhost:4317`（デフォルト）
- **エクスポート間隔**: メトリクス60秒、ログ5秒

### 設定のカスタマイズ

1. `otel_config.env`を編集（初回は自動作成される）
2. 必要に応じてエンドポイントや認証情報を設定
3. デバッグ時は`OTEL_METRICS_EXPORTER=console,otlp`でconsole出力も有効化可能

## 🏷️ エージェント識別

各エージェントは以下の属性でタグ付けされます：

- `agent.id`: エージェントID（例：`PG1.1.1`）
- `agent.type`: エージェントタイプ（例：`PG`、`CI`、`SE`）
- `team.id`: チームID（例：`team.1.1`）
- `working.dir`: 作業ディレクトリ

## 📈 収集されるメトリクス

### 標準メトリクス（Claude Code提供）
- `claude_code.session.count`: セッション数
- `claude_code.token.usage`: トークン使用量
- `claude_code.cost.usage`: コスト
- `claude_code.code_edit_tool.decision`: ツール使用判断
- `claude_code.lines_of_code.count`: コード行数変更
- `claude_code.commit.count`: コミット数

### カスタム属性
すべてのメトリクスにエージェント情報が付与され、以下の分析が可能：
- エージェント別のトークン消費量
- チーム別のコスト集計
- 役割別のツール使用パターン

## 🔧 バックエンドとの接続

### 推奨構成

1. **ローカル開発環境**
   ```bash
   # Docker ComposeでOTel CollectorとGrafanaを起動
   docker-compose -f telemetry/docker-compose.yml up -d
   ```

2. **本番環境**
   - Grafana Cloud
   - LangFuse（OpenTelemetry対応）
   - Datadog
   - その他OTLP対応サービス

### LangFuse統合（オプション）

LangFuseはOpenTelemetryトレーシングをサポート：

```bash
# otel_config.envを編集
export OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/otlp
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your-langfuse-token"
```

## 🛠️ トラブルシューティング

### メトリクスが送信されない場合

1. エンドポイントの確認
   ```bash
   telnet localhost 4317
   ```

2. 環境変数の確認
   ```bash
   env | grep OTEL
   ```

3. デバッグモードで確認
   ```bash
   # otel_config.envを編集
   export OTEL_METRICS_EXPORTER=console,otlp
   export OTEL_METRIC_EXPORT_INTERVAL=10000  # 10秒
   ```

### consoleログが表示される場合

`otel_config.env`が正しく読み込まれているか確認してください。
起動時に「✅ Loaded OpenTelemetry configuration」が表示されることを確認。

## 📚 参考資料

- [Claude Code監視ドキュメント](https://docs.anthropic.com/ja/docs/claude-code/monitoring-usage)
- [OpenTelemetry仕様](https://opentelemetry.io/docs/)
- Issue #10, #12（本プロジェクト）