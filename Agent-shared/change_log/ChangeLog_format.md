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

- **生成時刻**: `[YYYY-MM-DDTHH:MM:SSZ]` ※UTC
- [x/✗] **compile**
    - status: `[success/warning/error]`
    - message: "[エラーや警告の内容]" ※エラー/警告時のみ
    - log: `[ログファイルパス]`
- [x/✗] **job**
    - id: `[ジョブID]`
    - resource_group: `[リソースグループ名]` # 予算計算に必須
    - start_time: `[YYYY-MM-DDTHH:MM:SSZ]` # 予算計算に必須
    - end_time: `[YYYY-MM-DDTHH:MM:SSZ]` # 完了時必須（またはcancelled_time）
    - runtime_sec: `[秒数]` # 実行時間（秒）
    - status: `[success/error/timeout/cancelled/running]`
- [x/✗] **test**
    - status: `[pass/fail]`
    - performance: `[数値]`
    - unit: `[単位]`
    - accuracy: `[精度値]` ※必要に応じて
- [x/✗] **sota**
    - scope: `[local/hardware/project]` ※更新時のみ
- **params**:
    - nodes: `[ノード数]`
    - その他の実行パラメータ

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
- 変更点
- compile情報（status）
- details内の項目:
  - 生成時刻（UTC形式: YYYY-MM-DDTHH:MM:SSZ）
  - job実行時の予算関連項目:
    - resource_group（リソースグループ名）
    - start_time（開始時刻）
    - end_time（終了時刻）またはcancelled_time（キャンセル時刻）
    - runtime_sec（実行時間（秒））

#### İsteğe bağlı alanlar
- message (hata/uyarı durumunda zorunlu)
- accuracy (hassasiyet önemliyse)
- sota (kayıt güncellendiğinde)
- Diğer params (uygulamaya göre değişir)

## PG tarafından ekleme usulü

### PG (Programcı) sorumlulukları
1. 新バージョンエントリの作成
2. 変更点とコメントの記述
3. **生成時刻の記録**（details内の最初に記載）
4. compile実行とstatus記録
5. 基本的なparams設定
6. compile結果の更新（status, log, message）
7. job情報の追記（id, status）
8. **Bütçe ile ilişkili bilgilerin kaydı** (resource_group, start_time, end_time, runtime_sec)
9. test sonuçlarının güncellenmesi
10. Performans değerlerinin kaydı

## Sürümleme kuralları
**Önemli**: Temel olarak `v1.0.0` ile başlayın. `v0.x.x` sadece mevcut kod çalışmıyorsa kullanılır.

- **Majör**: Büyük algoritma değişiklikleri, geriye dönük uyumsuz değişiklikler
- **Minör**: Özellik eklemeleri, performans iyileştirmeleri, yeni optimizasyon yöntemleri
- **Yama**: Hata düzeltmeleri, parametre ayarları (blok boyutu, iş parçacığı sayısı vb.), küçük ayarlamalar
