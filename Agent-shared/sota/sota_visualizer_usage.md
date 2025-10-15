# SOTA Visualizer Kullanım Kılavuzu (Pipeline Edition)

## Genel Bakış
`sota_visualizer.py`, VibeCodeHPC projesinin 4 katmanlı SOTA (State-of-the-Art) performans değişimini verimli bir şekilde görselleştiren pipeline tipi bir araçtır. Bellek verimliliği ve depolama IO optimizasyonu sayesinde büyük ölçekli projelerde bile hızlı çalışır.

## SOTA Katmanlarının Tanımı

### 4 Katman
1. **Local**: Her teknoloji dizini için en yüksek performans
   - Grafik sayısı = teknoloji dizinlerinin kümülatif sayısı
   - Örnek: intel2024_OpenMP, gcc11.3.0_MPI...
   - Her grafik tek mavi eğri

2. **Family**: 2. nesil füzyon teknolojisi ve üst teknolojilerinin karşılaştırması
   - Grafik sayısı = füzyon teknolojilerinin sayısı (OpenMP_MPI, OpenMP_AVX2 vb.)
   - **Çoklu eğri grafiği**: Füzyon teknolojisi ve üst teknolojiler aynı anda gösterilir
   - Örnek: OpenMP_MPI grafiğinde 3 eğri (OpenMP_MPI, OpenMP tek başına, MPI tek başına)
   - Her eğri farklı renkte otomatik atanır

3. **Hardware**: Donanım yapılandırmasında en yüksek performans
   - **Derleyici bazında**: single-node_gcc11.3.0, single-node_intel2024 vb.
   - **Donanım geneli**: single-node_all (tüm derleyiciler birleştirilmiş)
   - Örnek: single-node_all tüm derleyicilerin verilerini birleştiren en yüksek performans değişimi

4. **Project**: Proje genelinde en yüksek performans
   - Grafik sayısı = 4 (time/count × linear/log)
   - Tüm verileri birleştiren nihai performans değişimi

## Temel Kullanım

### Pipeline Modu (önerilen)
```bash
# Varsayılan yürütme (local→hardware→project sırasıyla verimli işleme)
python Agent-shared/sota/sota_visualizer.py

# Debug modu (düşük çözünürlük ile hızlı)
python Agent-shared/sota/sota_visualizer.py --debug

# Özet gösterimi (grafik oluşturma yok, yalnızca veri doğrulama)
python Agent-shared/sota/sota_visualizer.py --summary

# Yalnızca belirli seviye yürütme
python Agent-shared/sota/sota_visualizer.py --levels local,project

# Belirli PG'yi yüksek çözünürlükle
python Agent-shared/sota/sota_visualizer.py --specific PG1.2:150
```

### Yürütme Akışı (önemli)
**Otomatik periyodik yürütme (SE dokunmaz)**:
- PM'nin hooks'u ile zaten otomatik başlatılmış olmalıdır
- **15 dakikada bir** `User-shared/visualizations/sota/` dizinine PNG oluşturulur
- SE periyodik yürütmeyi başlatmaya gerek yok (zaten çalışıyor)
- Frekans değişikliği için `Agent-shared/periodic_monitor_config.txt` dosyasında `SOTA_INTERVAL_MIN=10` gibi ayarlayın

**SE'nin doğrulama çalışması**:
```bash
# PNG oluşturulmasını doğrula (görselleri doğrudan görme)
ls -la User-shared/visualizations/sota/**/*.png

# Veri bütünlüğünü doğrula
python Agent-shared/sota/sota_visualizer.py --summary

# Sorun varsa debug moduyla araştır
python Agent-shared/sota/sota_visualizer.py --debug --levels local
```

**SE'nin özelleştirme çalışması**:
- Projeye özgü ChangeLog formatına göre `_parse_changelog()` fonksiyonunu düzenle
- Performans değerinin birimi farklıysa düzenli ifadeyi ayarla
- Gerekirse katman belirleme mantığını iyileştir

## Seçenekler

### X Ekseni Seçimi
```bash
# Geçen süre bazlı (varsayılan)
python Agent-shared/sota/sota_visualizer.py --x-axis time

# Güncelleme sayısı bazlı
python Agent-shared/sota/sota_visualizer.py --x-axis count
```

### Y Ekseni Ölçeği
```bash
# Doğrusal ölçek (varsayılan)
python Agent-shared/sota/sota_visualizer.py

# Logaritmik ölçek (performans farkı büyükse etkili)
python Agent-shared/sota/sota_visualizer.py --log-scale
```

### Teorik Performans Gösterimi
```bash
# Teorik performansı göster (varsayılan)
python Agent-shared/sota/sota_visualizer.py

# Teorik performansı gizle
python Agent-shared/sota/sota_visualizer.py --no-theoretical

# Teorik performans bilinmiyorsa üst sınır ayarı (en yüksek performansın %10 üstü varsayılan)
python Agent-shared/sota/sota_visualizer.py --theoretical-ratio 0.2  # %20 üste ayarla
```

### Debug İşlevleri
```bash
# Özet gösterimi (grafik oluşturma yok, yalnızca veri doğrulama)
python Agent-shared/sota/sota_visualizer.py --summary

# Çıktı örneği:
# [PROJECT]
#   Genel: 
#     (120.5m, 234.5 GFLOPS)
#     (145.2m, 256.7 GFLOPS)
#     ... ve 23 nokta daha
# [TICK CHECK]
#   Max time: 17.3 saat
#   Tahmini ticks: 1038
#   ⚠️ UYARI: MAXTICKS sınırını aşacak!
#   ✅ Düzeltme uygulandı: MaxNLocator(nbins=15)

```

## Çıktı Konumu (v2'deki iyileştirme)
- Oluşturulan grafikler: `/User-shared/visualizations/sota/[katman]/`
  - `/sota/project/` - Proje geneli
  - `/sota/hardware/` - Donanım yapılandırması bazında
  - `/sota/family/` - Ara katman yazılımı katmanı bazında
  - `/sota/local/` - PG aracısı bazında
  - `/sota/comparison/` - Karşılaştırma grafikleri
- Rapor: `/User-shared/reports/sota_visualization_report.md`

## ChangeLog.md Okuma Mantığı

### Desteklenen Format
```markdown
### v1.0.0
**Değişiklikler**: "OpenMP paralelleştirme uygulaması"
**Sonuç**: Teorik performansın %65.1'i elde edildi `312.4 GFLOPS`
**Yorum**: "İlk uygulama"

<details>

- **Oluşturma zamanı**: `2025-01-30T12:00:00Z`
- [x] **test**
    - performance: `312.4`
    - unit: `GFLOPS`

</details>
```

**Önemli**: Oluşturma zamanı `<details>` etiketi içinde belirtilmelidir

### Birimin Otomatik Dönüşümü
- **TFLOPS → GFLOPS**: Otomatik olarak 1000 ile çarpılarak birleştirilir
- **Yürütme süresi → İş çıkarma**: ms/sec durumunda ters alınarak performans göstergesine dönüştürülür
- **Diğer birimler**: GB/s, fps vb. de olduğu gibi kullanılabilir

### SOTA Değerlendirmesi
- Her katmanda **monoton artan** grafik oluşturulur (yalnızca performans artışında plot)
- Merdiven şeklindeki grafikle SOTA güncelleme zamanlaması görsel olarak ifade edilir

## Roofline Model Benzeri Gösterim

### Teorik Performansın Alınması
1. `hardware_info.md`'den otomatik okuma
2. Bulunamazsa en yüksek performansın belirtilen oranı üstüne ayarlanır
3. Kırmızı kesikli çizgi ile teorik üst sınır gösterilir

### Dikkat Edilmesi Gerekenler
- Teorik performansa ulaşılması garanti değildir
- İlk aşamada en yüksek performansın %10 üstü varsayılan üst sınır olarak kullanılır
- `--theoretical-ratio` ile ayarlanabilir

## SE Aracısında Kullanım Örneği

### Veri Analizi ve Özelleştirme
```python
# Projeye özgü ChangeLog formatına uyum
# sota_visualizer.py'deki _parse_changelog() fonksiyonunu doğrudan düzenle

def _parse_changelog(self, path: Path) -> List[Dict]:
    """Projeye özgü format desteği"""
    entries = []
    
    # Örnek: Özel performans birimi "iterations/sec" kullanımı
    if 'iterations/sec' in line:
        match = re.search(r'([\d.]+)\s*iterations/sec', line)
        if match:
            # GFLOPS eşdeğer değerine dönüştür (projeye özgü hesaplama)
            current_entry['performance'] = float(match.group(1)) * 0.001
    
    # Örnek: Etiket formatı farklıysa
    elif line.startswith('## Version'):  # ### v yerine ## Version
        # Projeye göre ayarla
        ...
```

### Çoklu Proje Birleştirme
```bash
# Deney 1 verilerini dışa aktar
cd experiment1
python Agent-shared/sota/sota_visualizer.py --export

# Deney 2 verilerini dışa aktar  
cd ../experiment2
python Agent-shared/sota/sota_visualizer.py --export

# Daha sonra birleştirme betiği ile sentezle (SE'nin kendi oluşturması)
```

## Sorun Giderme

### Grafik Oluşturulmuyor
- ChangeLog.md'nin doğru formatta olup olmadığını doğrula
- Oluşturma zamanının (UTC) kaydedilip kaydedilmediğini doğrula
- Sonuçta sayı ve birimin bulunup bulunmadığını doğrula

### Teorik Performans Gösterilmiyor
- hardware_info.md'de "teorik performans" yazılıp yazılmadığını doğrula
- `--theoretical-ratio` ile manuel ayarlama da mümkün

### Performans Doğru Karşılaştırılamıyor
- Birimin birleştirilip birleştirilmediğini doğrula (GFLOPS önerilir)
- Yürütme süresi durumunda otomatik olarak ters dönüştürülür

