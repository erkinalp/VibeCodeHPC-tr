# 🤖 Claude Code Alt Aracı Kullanım Kılavuzu

## Genel Bakış

Claude Code’un `-p {sorgu}` seçeneğini kullanan alt aracı özelliği, büyük veri ve görselleri verimli biçimde işlemek için güçlü bir araçtır. Bu, VibeCodeHPC’deki PM, SE, PG, CD rollerinden ayrı, tamamlayıcı bir özelliktir; tüm aracılar gerektiğinde kullanabilir.

### Başlıca avantajlar
- **Bağlam tüketimini azaltır**: Ana aracının bağlamını korur
- **İşlem performansını artırır**: Büyük veride ön işleme verimliliği
- **Sabit plan kapsamında**: Claude Code Pro Max planına dahildir

## Temel kullanım

### 1. Basit sorgu çalıştırma
```bash
# Tek seferlik bir sorgu çalıştırıp sonucu alın
claude -p "Bu günlük dosyasından yalnızca hata mesajlarını çıkar ve özetle"

# Pipe ile giriş
cat large_log_file.txt | claude -p "Hataları türlerine göre sınıflandır ve özetle"
```

### 2. Görsel analizi
```bash
# Görsel içeriğini analiz et
claude -p "Bu ekran görüntüsünde tmux pencere/pane düzenini açıkla" < screenshot.png

# Birden çok görseli karşılaştırma
claude -p "Çalıştırma öncesi ve sonrası grafik farklarını analiz et" < performance_comparison.png
```

### 3. Büyük veride ön işleme
```bash
# Büyük ChangeLog.md’den önemli bilgileri ayıkla
claude -p "Yalnızca SOTA güncellemesi olan maddeleri listele" < changelog_unified.md

# JSON formatında yapılandırılmış veri al
claude -p "Performans verilerini zaman serisi halinde JSON formatında düzenle" --output-format json < performance_logs.txt
```

## Önerilen kullanım durumları

### ✅ Aktif olarak kullanılmalı

1. **Büyük günlük dosyalarının analizi**
   ```bash
   # 100MB’den büyük iş çalıştırma günlüklerinden sadece gereken bilgileri çıkar
   claude -p "Paralelleştirmenin etkili olduğu bölümleri belirle" < job_12345.out
   ```

2. **Görsel ve grafik analizi**
   ```bash
   # Performans grafiğinden somut sayıları oku
   claude -p "Bu grafikten her paralelleştirme yönteminin performans artış oranını sayısal ver" < sota_graph.png
   ```

3. **Birden çok dosyanın bütünleşik analizi**
   ```bash
   # Her PG’nin ChangeLog.md dosyalarını birleştirerek analiz et
   for file in PG*/ChangeLog.md; do
     echo "=== $file ===" 
     cat "$file"
   done | claude -p "Tüm PG’lerin ilerlemesini yatay analiz et ve başarı kalıplarını çıkar"
   ```

4. **Test kodunun otomatik üretilmesi**
   ```bash
   # Mevcut koddan test örnekleri üret
   claude -p "Bu kod için birim testleri üret" < matrix_multiply_v3.2.1.c
   ```

### ⚠️ Kaçınılması gereken kullanım durumları

- Küçük dosyaların (birkaç KB) basit okunması
- Aracılar arası iletişim (agent_send.sh kullanın)
- Proje düzeyinde karar gerektiren görevler

## 高度な使用例

### ストリーミングJSON出力で進捗確認
```bash
# リアルタイムで処理状況を確認
claude -p "Tüm hataları sınıflandır ve çözüm önerileri sun" \
  --output-format stream-json \
  < massive_error_log.txt | \
  jq -r 'select(.type == "assistant") | .message.content'
```

### セッション管理で継続的な分析
```bash
# 初回分析でセッションIDを保存
result=$(claude -p "Performans verisinin ilk analizi" --output-format json < perf_data.csv)
session_id=$(echo "$result" | jq -r '.session_id')

# 追加の質問を同じコンテキストで実行
claude -p --resume "$session_id" "OpenMP ve MPI kombinasyonunun etkisi nedir?"
```

### カスタムシステムプロンプトで専門的な分析
```bash
# HPC専門家として分析
claude -p "Bu profil sonucunu analiz et" \
  --system-prompt "Sen bir HPC performans optimizasyon uzmanısın. Önbellek verimliliği ve bellek bant genişliğine odaklanarak analiz et."
  < profile_result.txt
```

## 実装例：SEエージェントでの活用

```bash
#!/bin/bash
# SE用の統計分析スクリプト例

analyze_all_changes() {
    local target_dirs=("$@")
    local analysis_prompt="以下の観点で分析してJSON形式で出力:
    1. 各並列化手法の成功率
    2. 性能向上の平均値と分散
    3. 最も効果的だった最適化手法TOP5
    4. 失敗パターンの共通点"
    
    # 全ChangeLog.mdを結合
    for dir in "${target_dirs[@]}"; do
        find "$dir" -name "ChangeLog.md" -exec cat {} \;
    done | claude -p "$analysis_prompt" --output-format json
}

# 使用例
result=$(analyze_all_changes "Flow/TypeII/single-node")
echo "$result" | jq '.result' | python3 create_performance_graph.py
```

## コスト効率の良い使い方

1. **バッチ処理**: 複数の小さなクエリは1つにまとめる
2. **前処理の活用**: grepやawkで事前にデータを絞る
3. **キャッシュの活用**: 同じ分析は結果を保存して再利用

```bash
# 効率的な例：事前にフィルタリング
grep -E "SOTA|performance" ChangeLog.md | \
  claude -p "性能向上があった項目だけをまとめて"

# 非効率な例：全データを渡す
claude -p "ChangeLog.mdからSOTAに関する行だけ抽出して" < ChangeLog.md
```

## 注意事項

- サブエージェントは独立したコンテキストを持つため、メインエージェントの作業内容は引き継がれません
- 大量のデータを扱う際は、まず必要な部分だけを抽出してから渡すことを推奨
- `-p` オプションは非対話モードのため、確認や追加質問はできません

## まとめ

Claude Codeのサブエージェント機能は、VibeCodeHPCプロジェクトにおける大規模データ処理の強力な補助ツールです。適切に活用することで、メインエージェントのコンテキストを保護しながら、効率的な分析と処理が可能になります。
