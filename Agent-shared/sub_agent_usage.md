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

## Gelişmiş kullanım örnekleri

### Akış JSON çıktısıyla ilerleme takibi
```bash
# İşlem durumunu gerçek zamanlı kontrol et
claude -p "Tüm hataları sınıflandır ve çözüm önerileri sun" \
  --output-format stream-json \
  < massive_error_log.txt | \
  jq -r 'select(.type == "assistant") | .message.content'
```

### Oturum yönetimiyle süreğen analiz
```bash
# İlk analizde oturum kimliğini kaydet
result=$(claude -p "Performans verisinin ilk analizi" --output-format json < perf_data.csv)
session_id=$(echo "$result" | jq -r '.session_id')

# Ek soruları aynı bağlamla yürüt
claude -p --resume "$session_id" "OpenMP ve MPI kombinasyonunun etkisi nedir?"
```

### Özel sistem istemiyle uzman analiz
```bash
# HPC uzmanı olarak analiz et
claude -p "Bu profil sonucunu analiz et" \
  --system-prompt "Sen bir HPC performans optimizasyon uzmanısın. Önbellek verimliliği ve bellek bant genişliğine odaklanarak analiz et."
  < profile_result.txt
```

## Uygulama örneği: SE aracısıyla kullanım

```bash
#!/bin/bash
# SE için istatistik analiz betiği örneği

analyze_all_changes() {
    local target_dirs=("$@")
    local analysis_prompt="Aşağıdaki açılardan analiz et ve JSON biçiminde çıktı ver:
    1. Her paralelleştirme yönteminin başarı oranı
    2. Performans artışının ortalaması ve varyansı
    3. En etkili 5 optimizasyon yöntemi
    4. Başarısızlık kalıplarının ortak noktaları"
    
    # Tüm ChangeLog.md dosyalarını birleştir
    for dir in "${target_dirs[@]}"; do
        find "$dir" -name "ChangeLog.md" -exec cat {} \;
    done | claude -p "$analysis_prompt" --output-format json
}

# 使用例
result=$(analyze_all_changes "Flow/TypeII/single-node")
echo "$result" | jq '.result' | python3 create_performance_graph.py
```

## Maliyet verimli kullanım

1. **Toplu işlem**: Birden çok küçük sorguyu tek bir seferde birleştir
2. **Ön işleme**: grep/awk ile veriyi önceden daralt
3. **Önbellekten yararlan**: Aynı analizde sonuçları kaydet ve tekrar kullan

```bash
# Verimli örnek: Ön filtreleme
grep -E "SOTA|performance" ChangeLog.md | \
  claude -p "Yalnızca performans artışı olan öğeleri özetle"

# Verimsiz örnek: Tüm veriyi aktarmak
claude -p "ChangeLog.md’den yalnızca SOTA ile ilgili satırları çıkar" < ChangeLog.md
```

## Dikkat edilecekler

- Alt aracı bağımsız bir bağlama sahiptir; ana aracının çalışması otomatik devralınmaz
- Büyük veride önce gerekli kısımları ayıklayıp sonra aktarın
- `-p` seçeneği etkileşimsiz moddur; onay veya ek soru sorulamaz

## Özet

Claude Code’un alt aracı özelliği, VibeCodeHPC projelerinde büyük veriyi işlemek için güçlü bir yardımcı araçtır. Doğru kullanıldığında, ana aracının bağlamını korurken verimli analiz ve işlemeyi mümkün kılar.
