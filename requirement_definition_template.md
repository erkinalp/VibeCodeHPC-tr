# Gereksinim Tanımı
(Requirement Definition)

## Proje Bilgileri
- **Proje adı**: [Proje adını girin]
- **Oluşturma tarihi**: [YYYY-MM-DD biçiminde tarih girin]

## Optimizasyon Kapsamı
### Kodun temin yöntemi
- [ ] Yerel dosya: [Dizin yolunu belirtin]
- [ ] GitHub deposu: [URL belirtin]
- [ ] Diğer: [Temin yöntemini yazın]

### Hedef dosyalar
- **Ana dosya**: [Dosya adını yazın]
- **Bağımlı dosyalar**: [Bağımlılıkları listeleyin]

## Optimizasyon hedefi
### Performans hedefi
- **Hedef performans**: [Somut hedef; örn: mevcut performansın 2 katı]

### Öncelikler
- [ ] Çalışma süresini en aza indirme
- [ ] Bellek kullanımını en aza indirme
- [ ] Enerji verimliliğini en üst düzeye çıkarma
- [ ] Ölçeklenebilirliği artırma
- [ ] Diğer: [Açıklayın]

## Genel Bakış
### Uygulama özeti
[Uygulamanın özetini kısaca yazın]

### Optimizasyon yaklaşımı
[Tercih edilen bir yaklaşım varsa yazın; yoksa VibeCodeHPC otomatik belirler]

## Kısıtlar (belirtiniz)

### Donanım (alt sistemler)
#### Seçilen süperbilgisayar
- **Sistem adı**: [Süperbilgisayar adını yazın]

#### Kullanılabilir donanım
- [ ] [Kullanılabilir düğüm tiplerini seçin]

### SSH tarafında kullanılacak dizin
[Uzak ortamda dizin yolu veya _remote_info içinde belirtin]

### İş kaynakları (düğüm sayısı)
#### Kademeli ölçekleme
[Düğüm sayısı kullanım politikasını yazın]

#### Kaynak kısıtları
- Azami çalışma süresi: [Süre sınırını yazın]
- Diğer kısıtlar: [Varsa yazın]

#### İş çalıştırma yöntemi
- [ ] Batch job (önerilir)
- [ ] Etkileşimli job
- [ ] Login düğümünde çalıştırma (önerilmez)

Not: Aksi belirtilmedikçe VibeCodeHPC batch job ile çalıştırır.
Birçok süperbilgisayarda login düğümünde hesaplama yasaktır;
batch veya etkileşimli job kullanımını kuvvetle öneririz.

### Yazılım ortamı (derleyici ve paralelleştirme)
#### Derleyici seçenekleri
- [ ] [Kullanılabilir derleyicileri seçin]
- _remote_info’yu referans alarak kullanılabilir derleyicileri doğrulayın

#### Paralelleştirme kütüphaneleri
- [ ] MPI
- [ ] OpenMP
- [ ] CUDA
- [ ] OpenACC
- [ ] AVX/AVX2/AVX512 (SIMD komutları)
- [ ] Diğer: [Yazın]

#### Sayısal hesaplama kütüphaneleri
- [ ] Kullanma (yalnız kendi uygulamamız)
- [ ] Karşılaştırma için kullan (MKL, cuBLAS vb.)
- [ ] Aktif olarak kullan

### Paralelleştirme stratejisi (uygulama sırası/alanı)
[Özel bir strateji varsa yazın; yoksa VibeCodeHPC otomatik belirler]

### Kabul edilebilir doğruluk (test kodu belirt/üret)
#### Doğruluk gereksinimleri
- [ ] Mevcut testlerle aynı doğruluk
- [ ] Hata toleransı: [Ayrıntılı yazın]
- [ ] Diğer: [Yazın]

### Bütçe (iş)
#### Hesaplama kaynağı bütçesi
- **Alt sınır**: [En az bu puan kadar harcanır, optimizasyon sürer]
- **Hedef**: [Normal optimizasyon için beklenen bütçe]
- **Üst sınır**: [Aşılamayacak bütçe tavanı]

#### Puan tüketim oranı (referans)
[Süperbilgisayara göre puan tüketim oranını yazın. Ör: saniye başı 0.007 × GPU sayısı]

### CD (Git Agent) kullanımı
#### GitHub entegrasyonu
- [ ] Kullan
- [ ] Kullanma
- [ ] Kademeli geçiş

## Ek gereksinimler ve kısıtlar

### Zaman kısıtı
- **Alt sınır**: [Asgari çalışma süresi; ör: 1 saat]
- **Hedef**: [Standart çalışma süresi]
- **Üst sınır**: [Azami çalışma süresi; ör: 3 saat]

### Güvenlik gereksinimleri
- [ ] Süperbilgisayar/kullanıcı bilgilerinin anonimleştirilmesi (GitHub push öncesi)
- [ ] Bütçe bilgisinin göreceleştirilmesi (ekip toplam bütçesi kamuya açık değil)
- [ ] Mutlak yollardan kaçınma (taşınabilirlik)
- [ ] Diğer: [Yazın]

### Aracı yapısı
- [ ] SOLO modu (tek aracı tüm rolleri üstlenir)
- [ ] Çoklu aracı (PM, SE, PG, CD ayrı ayrı)

### Diğer yönergeler
[Aracılara ek talimatlar varsa yazın]

---

## Otomatik oluşturulan bilgiler (PM doldurur)
- **Eksik kalemler**: [PM otomatik doldurur]
- **Önerilen yapı**: [PM otomatik doldurur]
- **Başlangıç aracı yerleşimi**: [PM otomatik doldurur]
