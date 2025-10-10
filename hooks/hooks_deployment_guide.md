# VibeCodeHPC Claude Code Hooks Yerleştirme Kılavuzu (PM için)

## Genel Bakış
Claude Code hooks, aracının davranışlarını kontrol eden bir mekanizmadır. Özellikle:
- **Polling türü aracı (PM, SE, PG, CD)**: Bekleme durumunu engeller, sürekli aktif kalır
- **Tüm aracılar**: auto-compact sonrası gerekli dosyaların yeniden okunmasını teşvik eder

## Hooks sürümleri
v0.6.3 ve sonrasında, proje özelliklerine göre iki sürümden biri seçilebilir:

### v3 (varsayılan, önerilen)
- **Özellikler**: Dosya içeriğini olasılıksal olarak gömer, aracının özerkliğini vurgular
- **Ayar**: `Agent-shared/strategies/auto_tuning/auto_tuning_config.json` ile özelleştirilebilir
- **Kullanım**: Uzun soluklu projeler, auto-compact önlemleri, büyük ölçekli çoklu aracı

### v2
- **Özellikler**: Yalnızca dosya yollarını sağlar, hafif çalışır
- **Kullanım**: Kısa süreli projeler, deneysel değerlendirme, küçük projeler

### Sürüm seçimi
```bash
# v3 kullan (varsayılan)
./communication/setup.sh 12

# v2 kullan
./communication/setup.sh 12 --hooks v2
```

## Otomatik yerleştirme (önerilen)

### start_agent.sh ile yerleştirme
```bash
# Varsayılan (hooks ve telemetry her ikisi de etkin)
./communication/start_agent.sh PG1.1.1 /Flow/TypeII/single-node/intel2024/OpenMP

# Yalnızca hooks devre dışı
VIBECODE_ENABLE_HOOKS=false ./communication/start_agent.sh PG1.1.1 /path/to/dir

# Yalnızca telemetry devre dışı
VIBECODE_ENABLE_TELEMETRY=false ./communication/start_agent.sh PG1.1.1 /path/to/dir

# Her ikisi de devre dışı (hafif mod)
VIBECODE_ENABLE_HOOKS=false VIBECODE_ENABLE_TELEMETRY=false ./communication/start_agent.sh PG1.1.1 /path/to/dir
```

## Manuel yerleştirme (sorun giderme)

### 1. Bireysel aracıya yerleştirme
```bash
# Aracı tipini kontrol et
# PM, SE, PG, CD → polling

# hooksを配置
./hooks/setup_agent_hooks.sh SE1 /path/to/SE1/workdir polling
./hooks/setup_agent_hooks.sh PG1.1.1 /path/to/PG1.1.1/workdir polling
```

### 2. Yerleştirilen dosyalar
Her aracının çalışma dizinine aşağıdakiler yerleştirilir:
```
{AGENT_DIR}/
└── .claude/
    ├── hooks/
    │   ├── session_start.py  # Oturum başlangıcındaki işlem
    │   └── stop.py          # Bekleme sırasındaki işlem (türe göre)
    └── settings.local.json  # kancaları etkinleştirme ayarı
```

## Aracı türüne göre davranış

### Yoklama tipi (PM, SE, PG, CD)
- **Stop hook**: 待機を阻止し、定期タスクリストを提示
- **SessionStart hook**: 新規起動時に必須ファイルリスト提示
- **推奨巡回間隔**:
  - PM: 2-5分（全体監視）
  - SE: 3-10分（進捗監視、ジョブ時間に応じて調整）
  - PG: 1-3分（ジョブ実行結果確認）
  - CD: 非同期（GitHub同期）

## session_id takibi

### agent_and_pane_id_table.jsonl güncellemesi
Claude başladıktan sonra, SessionStart kancası otomatik olarak şunları yapar:
1. session_id’yi kaydeder
2. Aracının durumunu "running" olarak günceller
3. Çalışma dizinini (cwd) kaydeder

```jsonl
{"agent_id": "PG1.1.1", "tmux_session": "Team1_Workers1", "tmux_window": 0, "tmux_pane": 3, "claude_session_id": "abc123...", "status": "running", "cwd": "/VibeCodeHPC-jp/Flow/...", "last_updated": "2025-08-02T12:34:56Z"}
```

## トラブルシューティング

### hooks が動作しない場合
1. `.claude/hooks/` ディレクトリの存在確認
2. Pythonスクリプトの実行権限確認
3. `settings.local.json`のhooks有効化確認
4. Python3の利用可能性確認

### エージェントが頻繁に停止する場合
1. stop hookの`stop_hook_active`チェックが正常か確認
2. エージェントタイプの判定が正しいか確認
3. 必要に応じて`VIBECODE_ENABLE_HOOKS=false`で一時無効化

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
`hooks/templates/`にカスタムhookを追加して、setup_agent_hooks.shを修正することで、プロジェクト固有のhooksを配置できます。

### ⚠️ hooks無効化について（非推奨）

**重要**: hooksの無効化は強く非推奨です。ポーリング型エージェント（PM, SE, PG, CD）が待機状態に入り、プロジェクトが停止します。

どうしても無効化が必要な場合：
1. **プロジェクト開始前**に環境変数を設定
2. 全エージェントに影響することを理解する
3. MCPサーバ設定と`.claude/settings.local.json`の手動管理が必要

```bash
# プロジェクト開始前のみ（非推奨）
export VIBECODE_ENABLE_HOOKS=false
```

**推奨**: hooks機能は常に有効のまま使用してください。

## Başvuru Kaynakları
- Claude Code hooks resmi dokümantasyonu
- `hooks/templates/` içindeki betikler
- `telemetry/README.md` (telemetry ile entegrasyon)
