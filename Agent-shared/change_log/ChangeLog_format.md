# ChangeLog temel formatı

Bu belge, VibeCodeHPC projesinde ChangeLog.md için temel yazım biçimini tanımlar.

## Dosya yapısı

### 1. Üstbilgi bölümü
```markdown
# [Paralelleştirme modülü adı]📁 `ChangeLog.md`
🤖PG [Aracı ID]  
- **Donanım**: [Süperbilgisayar adı] [Düğüm tipi] ([Düğüm sayısı aralığı])  
- **Modül**: [Kullanılan derleyici/kütüphane] [Sürüm]  
```

### 2. Değişiklik günlüğü bölümü
```markdown
## Change Log

- Temel şablon: `ChangeLog_format.md` (ve PG tarafından ekleme usulü)
- PM üst yazımı: `ChangeLog_format_PM_override.md` (PM şablondan üretir)
```

### 3. Sürüm girdisi (yenisi üstte)

```markdown
### v[Majör].[Minör].[Yama]
**Değişiklikler**: "[Değişikliğin kısa açıklaması]"  
**Sonuç**: [En önemli sonuç] `[değer veya durum]`  
**Yorum**: "[Uygulama ayrıntıları ve dikkat noktaları]"  

<details>

- **Oluşturma zamanı**: `[YYYY-MM-DDTHH:MM:SSZ]` ※UTC
- [x/✗] **compile**
    - status: `[success/warning/error]`
    - message: "[Hata veya uyarı içeriği]" ※Hata/uyarı durumunda
    - log: `[Log dosya yolu]`
- [x/✗] **job**
    - id: `[İş ID]`
    - resource_group: `[Kaynak grubu adı]` # Bütçe hesabı için zorunlu
    - start_time: `[YYYY-MM-DDTHH:MM:SSZ]` # Bütçe hesabı için zorunlu
    - end_time: `[YYYY-MM-DDTHH:MM:SSZ]` # Tamamlandığında zorunlu (veya cancelled_time)
    - runtime_sec: `[Saniye]` # Yürütme süresi (saniye)
    - status: `[success/error/timeout/cancelled/running]`
- [x/✗] **test**
    - status: `[pass/fail]`
    - performance: `[Sayısal değer]`
    - unit: `[Birim]`
    - accuracy: `[Hassasiyet değeri]` ※Gerekirse
- [x/✗] **sota**
    - scope: `[local/hardware/project]` ※Güncelleme zamanında
- **params**:
    - nodes: `[Düğüm sayısı]`
    - Diğer yürütme parametreleri

</details>
```

## Yazım kuralları

### 1. Temel ilkeler
- **Dil**: Türkçe ile tutarlı
- **Sıra**: Yeni sürüm üstte (azalan)
- **Detay**: `<details>` etiketiyle katlayıp okunabilirliği koruyun

### 2. Onay kutularının kullanımı
- `[x]` - Tamamlanan adım
- `[ ]` - Tamamlanmamış veya başarısız adım

### 3. status değerleri
- **compile**: `success`, `warning`, `error`
- **job**: `success`, `error`, `timeout`, `cancelled`, `running`
- **test**: `pass`, `fail`, `partial`
- **sota**: Kapsam `local` (bu PG içinde), `family` (aynı ara katman içinde ebeveyn/çocuk nesiller), `hardware` (donanım bileşimi içinde), `project` (proje genelinde)

### 4. Zorunlu ve isteğe bağlı alanlar
#### Zorunlu alanlar
- version
- Değişiklikler
- compile bilgisi (status)
- details içindeki öğeler:
  - Oluşturma zamanı (UTC formatı: YYYY-MM-DDTHH:MM:SSZ)
  - İş yürütme sırasında bütçe ile ilgili öğeler:
    - resource_group (Kaynak grubu adı)
    - start_time (Başlangıç zamanı)
    - end_time (Bitiş zamanı) veya cancelled_time (İptal zamanı)
    - runtime_sec (Yürütme süresi (saniye))

#### İsteğe bağlı alanlar
- message (hata/uyarı durumunda zorunlu)
- accuracy (hassasiyet önemliyse)
- sota (kayıt güncellendiğinde)
- Diğer params (uygulamaya göre değişir)

## PG tarafından ekleme usulü

### PG (Programcı) sorumlulukları
1. Yeni sürüm girdisinin oluşturulması
2. Değişiklikler ve yorumların yazılması
3. **Oluşturma zamanının kaydı** (details içinde ilk sırada)
4. compile yürütme ve status kaydı
5. Temel params ayarları
6. compile sonuçlarının güncellenmesi (status, log, message)
7. job bilgilerinin eklenmesi (id, status)
8. **Bütçe ile ilişkili bilgilerin kaydı** (resource_group, start_time, end_time, runtime_sec)
9. test sonuçlarının güncellenmesi
10. Performans değerlerinin kaydı

## Sürümleme kuralları
**Önemli**: Temel olarak `v1.0.0` ile başlayın. `v0.x.x` sadece mevcut kod çalışmıyorsa kullanılır.

- **Majör**: Büyük algoritma değişiklikleri, geriye dönük uyumsuz değişiklikler
- **Minör**: Özellik eklemeleri, performans iyileştirmeleri, yeni optimizasyon yöntemleri
- **Yama**: Hata düzeltmeleri, parametre ayarları (blok boyutu, iş parçacığı sayısı vb.), küçük ayarlamalar
