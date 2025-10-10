# Bütçe Toplama Sistemi Kullanım Kılavuzu

## Genel Bakış
ChangeLog.md’de kaydedilen zaman bilgilerine dayanarak projenin bütçe tüketimini otomatik toplayan bir sistemdir.

## PG için: İş çalıştırma sırasında kayıt yöntemi

### 1. İş betiğine zaman kaydı ekleme
```bash
# スクリプト先頭
source $PROJECT_ROOT/Agent-shared/budget/job_time_template.sh
# または必要部分をコピー

# Kaynak grubunu belirtin (önemli)
RESOURCE_GROUP="cx-small"  # 使用するリソースグループ
```

### 2. ChangeLog.md’ye kayıt (zorunlu)
```markdown
### v1.2.0
**Değişiklikler**: "OpenMP paralelleştirme uygulaması"
**Sonuç**: Teorik performansın %65’i elde edildi `312.4 GFLOPS`

<details>

- **Oluşturma zamanı**: `2025-01-30T10:00:00Z`
- [x] **job**
    - id: `12345`
    - resource_group: `cx-small`  # Zorunlu: ücret hesabında kullanılır
    - start_time: `2025-01-30T10:00:00Z`  # Zorunlu
    - end_time: `2025-01-30T10:45:32Z`  # Zorunlu (tamamlandığında)
    - runtime_sec: `2732`  # Zorunlu (tamamlandığında)
    - status: `completed`

</details>
```

### 3. İptal durumunda kayıt
```markdown
- [ ] **job**
    - id: `12345`
    - resource_group: `cx-small`
    - start_time: `2025-01-30T10:00:00Z`
    - cancelled_time: `2025-01-30T10:15:00Z`  # end_time yerine
    - runtime_sec: `900`  # İptale kadar geçen çalışma süresi
    - status: `cancelled`
```

## SE için: Toplama ve izleme

### 1. Anlık tüketimi görüntüleme
```bash
# Projenin herhangi bir yerinden çalıştırılabilir
python Agent-shared/budget/budget_tracker.py --summary

# Örnek çıktı:
# === Bütçe Toplama Özeti ===
# Toplam tüketim: 1234.5 puan
# İş sayısı: tamamlandı=10, çalışıyor=2
# Alt sınır: 123.5%
# Hedef: 49.4%
# Üst sınır: 24.7%
```

### 2. Ayrıntılı rapor oluşturma
```bash
python Agent-shared/budget/budget_tracker.py --report

# snapshots/ içine şunlar oluşturulur:
# - budget_YYYY-MM-DDTHH-MM-SSZ.json(zaman damgalı)
# - latest.json(en güncel)
```

### 3. グラフ生成（デフォルトで自動生成）
```bash
# Varsayılan davranış (argümansız) ile grafik otomatik üretilir
python Agent-shared/budget/budget_tracker.py
# → User-shared/visualizations/budget_usage.png oluşturulur

# --graph seçeneği önerilmez (deprecated)
# Varsayılan olarak üretildiğinden ayrıca belirtmeye gerek yok
python Agent-shared/budget/budget_tracker.py --graph  # 非推奨
```

### 4. periodic_monitor.sh ile tümleştirme
```bash
# Her 3 dakikada bir otomatik toplama (periodic_monitor.sh içinde ayarlı)
if [ $((ELAPSED_MINUTES % 3)) -eq 0 ]; then
    python "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" --report
fi
```

### 5. JSON biçiminde alma (görselleştirme için)
```bash
python Agent-shared/budget/budget_tracker.py --json > budget.json
```

### 6. Belirli zamanda anlık görüntü (--as-of)
```bash
# Belirli zamana kadar olan veriyi topla ve görselleştir
python Agent-shared/budget/budget_tracker.py --as-of 2025-08-20T01:00:00Z

# Kilometre taşı anındaki toplama
python Agent-shared/budget/budget_tracker.py --graph --as-of 2025-08-19T23:30:00Z
```

## Kaynak grubu başına hızlar

### Furou TypeII (varsayılan ayar)
| Kaynak grubu | GPU sayısı | Hız (puan/saniye) |
|---------------|------|-------------------|
| cx-share      | 1    | 0.007            |
| cx-small      | 4    | 0.028            |
| cx-middle     | 4    | 0.028            |
| cx-middle2    | 4    | 0.056 (2x)       |

### Diğer süper bilgisayarlara uyarlama
`budget_tracker.py` içindeki `load_rates()` metodunu düzenleyin veya
`_remote_info/[süper bilgisayar adı]/node_resource_groups.md` yolundan otomatik yükleme (ileride)

## Sorun Giderme

### S: İşin puanı hesaplanmıyor
C: ChangeLog.md’de şu alanların olduğundan emin olun:
- resource_group(zorunlu)
- start_time(zorunlu)
- end_time veya cancelled_time (çalışma sonrası zorunlu)

### S: Toplama sonucu 0 puan
C: Proje başlangıç zamanının kaydedildiğini kontrol edin:
```bash
cat Agent-shared/project_start_time.txt
```

### S: Çalışan işler yansımıyor
C: status alanının `running` olduğundan emin olun. end_time yoksa mevcut zamana kadar hesaplanır.

## Dikkat Edilecekler

- **Durumsuz yürütme**: Her seferinde tüm ChangeLog.md dosyaları okunur; dosya çoksa zaman alabilir
- **Gerçek zamanlılık**: ChangeLog.md’ye yazma zamanlamasına bağlıdır (PG yazana kadar yansımaz)
- **Hassasiyet**: Saniye bazlı hesap nedeniyle gerçek ücretlendirmeye göre birkaç puan sapma olabilir
