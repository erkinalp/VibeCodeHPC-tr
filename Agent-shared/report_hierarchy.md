# Rapor Hiyerarşisi Kılavuzu

## Özet
VibeCodeHPC’de teknik ayrıntılardan yönetim özetine kadar 3 kademeli bir rapor yapısı kullanılır.

## Rapor kademeleri

### 1. Birincil rapor (saha düzeyi)
- **Biçim**: ChangeLog.md
- **Oluşturucu**: PG (gerçek zamanlı otomatik kayıt)
- **Konum**: Her PG’nin çalışma dizini
- **Özellikler**: 
  - Tüm teknik ayrıntıların kaydı
  - Sürümlere göre deneme-yanılma kayıtları
  - Çalıştırma günlüklerine giden yollar

### 2. İkincil rapor (entegrasyon düzeyi)
- **Biçim**: Markdown + görsel
- **Oluşturucu**: SE (Python ile yarı otomatik)
- **Konum**: User-shared/reports/
- **Özellikler**:
  - Birden çok PG çıktısının entegrasyonu
  - Grafiklerle görselleştirme
  - İnsan okunabilir biçim
  - Türkçe olarak yazılır

### 3. Nihai rapor (yönetim düzeyi)
- **Biçim**: Yönetici özeti
- **Oluşturucu**: PM
- **Konum**: User-shared/final_report.md
- **Özellikler**:
  - Yatırım-getiri oranının netleştirilmesi
  - Bütçe tüketimi ve çıktılar
  - İleriye dönük öneriler

## Dizin yapısı

```
VibeCodeHPC/
├── Agent-shared/                # Aracılar için (teknik)
│   ├── sota/
│   │   └── sota_visualizer.py  # SOTA görselleştirme aracı
│   └── budget/
│       └── budget_tracker.py   # Bütçe takip aracı
└── User-shared/                 # Kullanıcı için (çıktılar)
    ├── final_report.md          # Nihai rapor
    ├── reports/
    │   └── performance_summary.md
    └── visualizations/
        └── sota/                # SOTA可視化グラフ
```

## Rapor oluşturma zamanları

### Kısa süreli yoğun projelerde kullanım
- **Birincil**: PG kod üretiminde anında kayıt (ChangeLog.md)
- **İkincil**: SE gerektiğinde entegrasyon raporu oluşturur
- **Nihai**: PM proje sonunda oluşturur

### Oluşturma zamanlaması
- **Entegrasyon raporu**: Önemli dönüm noktalarında
- **Ara rapor**: Bütçenin %50 tüketiminde (önerilir)
- **Nihai rapor**: Proje tamamlandığında

## Dil kullanım rehberi

| Rapor türü | Dil | Gerekçe |
|------------|------|------|
| ChangeLog.md | Türkçe | Teknik terimler İngilizce olabilir |
| İkincil rapor | Türkçe | Kullanıcıya yönelik |
| Grafik etiketleri | Türkçe | Görünürlüğü artırır |
| Nihai rapor | Türkçe | Yönetim düzeyi |

## User-shared’in avantajları

1. **Erişilebilirlik**: Kullanıcı sadece buraya bakar
2. **Düzen**: Teknik ayrıntılar ile çıktıları ayırır
3. **Paylaşım**: Sunum malzemesi olarak derhal kullanılabilir
4. **Bakım**: Aracı araçlarından ayrıdır

## Dikkat edilmesi gerekenler

- Agent-shared/ altında aracılar arasında paylaşılan teknik araçları konumlandır
- User-shared/ altında yalnızca nihai çıktıları konumlandır
- Gizli bilgilerin yönetimine dikkat et (özellikle nihai rapor)
