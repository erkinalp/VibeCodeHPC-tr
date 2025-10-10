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
- [x] fjmpi-gcc (giriş düğümünde kullanılamaz; toplu veya etkileşimli işten kullanılmalıdır)

#### Paralelleştirme kütüphaneleri
- [x] MPI
- [x] OpenMP
- [x] ACLE (intrinsic tabanlı SIMD)

### Paralelleştirme stratejisi (uygulama sırası ve kapsam)
#### Uygulama aşaması
Evrimsel arama (çeşitli algoritmaların tasarım/keşfi ilgili PG’lere bırakılır)

#### Uygulama noktaları
Ağırlıklı olarak mat-mat(-d).c dosyasındaki My-mat-mat ve main fonksiyonu çağrısı öncesi/sonrası

### Kabul edilebilir doğruluk (test kodu belirtimi/üretimi)
#### Doğruluk gereksinimi
- [x] Mevcut testlerle aynı doğruluk

### Bütçe (iş)
#### Hesaplama kaynağı bütçesi
- **Asgari tüketim çizgisi**: 1.000 puan
- **Hedef aralık**: 3.000 puan
- **Üst sınır**: 10.000 puan
    TypeI: Geçen her saniye için 0.0056 puan × kullanılan düğüm sayısı
- 1 JPY başına 0.8 puan

#### Kısıtlar
- Azami yürütme süresi kural olarak 1 dakika olmalıdır
- Sadece büyük veri toplarken 10 dakikanın altı

### CD (Git Aracısı) kullanımı
#### GitHub entegrasyonu
- [x] Kullanılacak
- [ ] Kullanılmayacak
- [ ] Aşamalı devreye alma

#### Bildirim ayarı
- Gereksiz

## Ek gereksinimler ve kısıtlar
### Güvenlik gereksinimleri
- **Gizlilik seviyesi**: BaseCode GitHub’da (özel depo) kopyalanabilir
- **Veri koruma**: Süperbilgisayar ve kullanıcı bilgileri GitHub’a push etmeden önce anonimleştirilecektir

### Uyumluluk gereksinimleri
- **Diğer sistem entegrasyonu**: Yok
- **Çıktı formatı**: Performans verileri CSV formatında çıktı

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
- **Başlangıç aracı yerleşimi**: [otomatik]
