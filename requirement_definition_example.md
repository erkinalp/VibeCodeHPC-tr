# Gereksinim Tanımı
(Requirement Definition)

## Proje Bilgileri
- **Proje adı**: tmux_demo1
- **Oluşturulma tarihi**: 2025-07-23

## Optimizasyon Kapsamı
### Kod edinim yöntemi
- [x] Yerel dosyalar: BaseCode/ altı

### Hedef dosyalar
- **Ana dosyalar**: mat-mat.c, mat-mat-d.c
- **Bağımlı dosyalar**: mat-mat-.bash, Makefile

## Optimizasyon derecesi (hedef)
### Performans hedefi
- **Hedef performans**: Teorik tepe performansa yaklaşmak

### Öncelikler
- [x] Çalışma süresini en aza indirme
- [ ] Bellek kullanımını en aza indirme
- [ ] Enerji verimliliğini en üst düzeye çıkarma
- [x] Ölçeklenebilirliği artırma
- [ ] Diğer:

## Özet
### Uygulama özeti
Birden çok matris boyutu için, MPI süreç sayısı 1–576 (düğüm sayısı 1–12) aralığında yürütme süresi ölçülecektir.
MPI süreç sayısı 1 için ölçülen süre 1 kabul edilerek 576 sürece kadar hızlanma (ölçek etkisi) grafiği oluşturulacaktır.

### Optimizasyon yaklaşımı
Aşağıdakiler paralel olarak ilerletilecektir:

(i) Mat-Mat (iletişim fonksiyonu gerektirmeyen) örnek programı paralelleştirilecektir.
Burada A, B, C matrisleri için başlangıç durumunda her PE’de kopyalı veri bulunmasına izin verilir.

(ii) Mat-Mat-d (bire bir iletişim fonksiyonu gerektirir)
MPI süreç sayısı 1’deki yürütme, (i)’deki sıralı matris çarpım süresi ölçülerek referans alınacaktır.

## Kısıtlar (Belirtilen)

### Donanım (Alt sistem)
#### Seçilen süperbilgisayar
- **Sistem adı**: Furo (flow)

#### Kullanılabilir donanım
- [x] TypeI: 1–12 düğüm (iş başına)

### SSH tarafında kullanılacak dizin
_remote_info içinde belirtilir

### İş kaynakları (düğüm sayısı)
#### Aşamalı ölçekleme
- Her seferinde 1–576 düğüm denemek gerekmez
- Hata ayıklamada sadece 576 düğümde deneme gibi pratik çözüm uygulayın
- Matris boyutunu da aşamalı büyütün; saatler süren işler göndermekten kaçının

#### Kaynak kısıtları
- Azami yürütme süresi kural olarak 1 dakika olmalıdır
- Sadece büyük veri toplarken 10 dakikanın altı

#### İş yürütme yöntemi
- [x] Toplu iş (önerilir)
- [ ] Etkileşimli iş
- [ ] Giriş düğümünde yürütme (önerilmez)

### Ara katman (derleyici/paralelleştirme modülleri)
#### Derleyici seçenekleri
- [x] GCC 10.4.0 (default)
- [x] fjmpi-gcc ※ログインノードでは利用不可、バッチジョブまたはインタラクティブジョブから利用

#### Paralelleştirme kütüphaneleri
- [x] MPI
- [x] OpenMP
- [x] ACLE (intrinsicなSIMD)

### Paralelleştirme stratejisi (uygulama sırası ve kapsam)
#### Uygulama aşaması
Evrimsel arama (çeşitli algoritmaların tasarım/keşfi ilgili PG’lere bırakılır)

#### Uygulama noktaları
Ağırlıklı olarak mat-mat(-d).c dosyasındaki My-mat-mat ve main fonksiyonu çağrısı öncesi/sonrası

### Kabul edilebilir doğruluk (test kodu belirtimi/üretimi)
#### Doğruluk gereksinimi
- [x] 既存テストと同精度

### Bütçe (iş)
#### Hesaplama kaynağı bütçesi
- **最低消費ライン**: 1,000ポイント
- **目安**: 3,000ポイント
- **上限**: 10,000ポイント
    TypeI: Geçen her saniye için 0.0056 puan × kullanılan düğüm sayısı
- 1 JPY başına 0.8 puan

#### Kısıtlar
- Azami yürütme süresi kural olarak 1 dakika olmalıdır
- Sadece büyük veri toplarken 10 dakikanın altı

### CD (Git Aracısı) kullanımı
#### GitHub entegrasyonu
- [x] 使用する
- [ ] 使用しない
- [ ] 段階的導入

#### Bildirim ayarı
- Gereksiz

## Ek gereksinimler ve kısıtlar
### Güvenlik gereksinimleri
- **機密レベル**: BaseCodeはGitHub（Privateリポジトリ）にコピー可能
- **データ保護**: スパコン・ユーザ情報はGitHubにpushする前に匿名化

### Uyumluluk gereksinimleri
- **他システム連携**: 特になし
- **結果フォーマット**: CSV形式で性能データを出力

### Diğerleri
- Bu, VibeCodeHPC’nin tmux tabanlı paralel aracı yapısının bir testidir
#### CD
- GitHub’ı yöneten CD aracı, performanstan bağımsız tüm üretilen sürüm kodlarını push etmelidir
- Commit’leri mesaj yazmayı kolaylaştıracak mantıksal parçalarda yapın
- GitHub/📁 altındaki .gitignore’ı proje kökünden kopyalayıp gerekirse düzenleyin
- Bu requirement_definition.md vb. dosyaları anonimleştirip push edin. Gerçek kimlikleri anonimleştiren .py/.sh araçlarını Git dışında üretip kullanabilirsiniz

---

## Otomatik üretilen bilgiler (PM doldurur)
- **Eksik kalemler**: [otomatik]
- **Önerilen yapı**: [otomatik]
- **初期エージェント配置**: [自動記入]
