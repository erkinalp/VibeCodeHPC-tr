# SOTA Checker Kullanım Kılavuzu

## Genel Bakış
`sota_checker.py`, VibeCodeHPC projesinin 4 katmanlı SOTA (State-of-the-Art) değerlendirmesini yapar ve kaydeder.
PG aracısı yeni bir performans değeri elde ettiğinde çalıştırılır ve her katmanın sota_*.txt dosyalarını otomatik olarak günceller.

## 4 Katmanlı SOTA
1. **Local**: Her teknoloji dizini için en yüksek performans (sota_local.txt)
2. **Family**: Virtual Parent (üst teknoloji) ile karşılaştırma (çalışma zamanında hesaplanır, dosya çıktısı yok)
3. **Hardware**: Donanım yapılandırmasında en yüksek performans (sota_hardware.txt)
4. **Project**: Proje genelinde en yüksek performans (sota_project.txt)

## Kullanım Yöntemi

### Komut Satırı Yürütme
```bash
# Temel format
python Agent-shared/sota/sota_checker.py <performans_değeri> [dizin] [sürüm] [agent_id]

# PG kendi dizininde yürütür (göreli yol kullanımı)
python ../../../../../../Agent-shared/sota/sota_checker.py "350.0 GFLOPS" . v1.2.3 PG1.1

# SOLO proje kök dizininden herhangi bir dizini belirtir
python Agent-shared/sota/sota_checker.py "350.0 GFLOPS" Flow/TypeII/single-node/intel2024/OpenMP v1.2.3 SOLO
```

### Python İçinde Kullanım
```python
import sys
from pathlib import Path

# Agent-shared/sota'yı yola ekle
sys.path.append(str(Path(__file__).parent / "../../../../../../Agent-shared/sota"))
from sota_checker import SOTAChecker

# Mevcut dizinde SOTA değerlendirmesi
checker = SOTAChecker(".")
results = checker.check_sota_levels("350.0 GFLOPS")

# Sonuç doğrulama
for level, is_sota in results.items():
    if is_sota:
        print(f"{level}: YENİ SOTA!")

# SOTA dosyası güncelleme (herhangi bir katmanda SOTA başarısı durumunda)
if any(results.values()):
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    checker.update_sota_files("v1.2.3", timestamp, "PG1.1")
```

## Yürütme Zamanlaması
1. **ChangeLog.md güncellemesinden sonra**: Yeni sürümün performans ölçümü tamamlandığında yürüt
2. **İş yürütme sonucu alındıktan sonra**: Performans değeri kesinleştiğinde
3. **SOTA değerlendirmesi gerektiğinde**: PM veya SE'den talimat geldiğinde

## Dosya Yerleşimi
```
VibeCodeHPC/
├── sota_project.txt              # Project katmanı SOTA
├── Flow/TypeII/single-node/
│   ├── sota_hardware.txt         # Hardware katmanı SOTA
│   └── intel2024/OpenMP/
│       ├── ChangeLog.md          # Performans kaydı
│       └── sota_local.txt        # Local katmanı SOTA
```

## Virtual Parent (Family) Hakkında
- **Dosya çıktısı yok**: Family katmanı çalışma zamanında dinamik olarak hesaplanır
- **Başvuru kaynağı**: PG_visible_dir.md'nin "Virtual parent" bölümü
- **Örnek**: OpenMP_MPI'nin üst teknolojisi OpenMP ve MPI'dır (aynı derleyici altında)

## Dikkat Edilmesi Gerekenler
- Performans değeri mutlaka `"XXX.X GFLOPS"` formatında belirtilmelidir
- Dizin belirtilmediğinde mevcut dizin kullanılır
- Göreli yol ve mutlak yol her ikisi de desteklenir
- Proje adının "VibeCodeHPC" ile başladığı varsayılır

## Sorun Giderme
- **"Project root not found"**: Proje kök dizini bulunamadı
  - Çözüm: Mutlak yol ile yürüt veya proje içinden yürüt
- **"sota_local.txt not found"**: İlk yürütmede normaldir (dosya oluşturulur)
- **İzin hatası**: sota_*.txt yazma izinlerini doğrula

