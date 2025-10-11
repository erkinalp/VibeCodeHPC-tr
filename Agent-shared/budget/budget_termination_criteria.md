# Bütçe Kriterine Dayalı Proje Sonlandırma Koşulları

## Genel Bakış
Projenin sonlandırma kararını PM'nin öznel yargısına değil, süper bilgisayar bütçesinin (hesaplama noktası) tüketim durumuna dayalı olarak nesnel bir şekilde vermek.

## Temel İlkeler
- **Öznel yargının ortadan kaldırılması**: PM'nin "artık bitirme zamanı" gibi öznel yargısını tamamen ortadan kaldırmak
- **Şeffaflığın sağlanması**: Tüm aracıların sonlandırma koşullarını ve mevcut fazı anlayabilmesi
- **Aşamalı müdahale**: Bütçe tüketim oranına göre aşamalı eylem

## Bütçe Tüketimine Göre Aşamalı Müdahale

### 🔵 Faz 0: Ulaşılmamış Dönem (0-minimum tüketim miktarı)
- **Durum**: Minimum tüketim miktarına ulaşılmamış
- **Sorun**: Temel işlem doğrulaması bile tamamlanmamış
- **Müdahale**:
  - Giriş düğümü yürütme şüphesini hemen araştır
  - İş gönderme yöntemini doğrula
  - Ortam kurulum sorunlarını öncelikle çöz
  - PM'nin "artık bitirme zamanı" yargısını önlemek için aktif olarak yürüt

### 🟢 Faz 1: Aktif Keşif Dönemi (minimum tüketim-beklenen tüketimin %50'si)
- **Durum**: Temel işlem doğrulaması tamamlandı, bütçede bol marj var
- **Strateji**: 
  - Yeni optimizasyon tekniklerini aktif olarak dene
  - Birden çok parametreyi geniş bir aralıkta keşfet
  - Yüksek paralellik dereceli deneyleri öner

### 🟡 Faz 2: Verimlilik Odaklı Dönem (beklenen tüketimin %50-80'i)
- **Durum**: Sorunsuz ilerleme
- **Strateji**:
  - Sonuç veren tekniklere odaklan
  - Parametre ayarlamasının yakınsamasını göz önünde bulundur
  - Maliyet verimliliğini vurgula

### 🟠 Faz 3: Yakınsama Dönemi (beklenen tüketimin %80-100'ü)
- **Durum**: Beklenen tüketim miktarına yaklaşılıyor
- **Strateji**:
  - Yalnızca en umut verici optimizasyona devam et
  - Yeni uygulamaları dikkatle değerlendir
  - Sonuçların özetlenmesine başla

### 🔴 Faz 4: Uyarı Dönemi (beklenen tüketim-son tarihin %90'ı)
- **Durum**: Son tarihe yaklaşılıyor
- **Eylem**:
  - Yeni işler ön onay sistemine tabi
  - Çalışan işlerin erken sonlandırılmasını değerlendir
  - Nihai rapor hazırlığı

### ⛔ Faz 5: Zorunlu Sonlandırma (son tarihin %90-100'ü)
- **Durum**: Bütçe üst sınırına yakın
- **Eylem**:
  - Yeni iş tamamen yasak
  - Yalnızca önemli işlerin tamamlanmasını bekle
  - Tüm çalışmaları 5 dakika içinde sonlandır

## Bütçe Takip Yöntemi

### budget_history.md Kayıt Formatı
```markdown
## Proje başlangıcında
- UTC zamanı: 2025-01-30T10:00:00Z
- Başlangıç used: 12,345 nokta
- Minimum tüketim miktarı: 100 nokta (eski 500→gevşetildi)
- Beklenen tüketim: 1,000 nokta
- Son tarih: 1,500 nokta

## En son doğrulama
- UTC zamanı: 2025-01-30T12:00:00Z
- Şu anki used: 12,845 nokta
- **Bu projedeki kullanım: 500 nokta**
- Beklenen tüketime göre ilerleme: %50
- Son tarihe göre tüketim oranı: %25
- **Mevcut faz: 🟡 Faz 2: Verimlilik Odaklı Dönem**
```

### İzleme Komutu (süper bilgisayara bağlı)
- Furo: `charge`
- Diğerleri: `_remote_info/command.md`'ye bakın
- **Dikkat**: Her süper bilgisayarda bütçe doğrulama komutu farklıdır, mutlaka önceden doğrulayın

### Bütçe Verimliliği Metrikleri
```
Verimlilik skoru = (performans artış oranı) / (nokta tüketimi)

Değerlendirme kriterleri:
- Yüksek verimlilik: Skor > 0.1
- Standart: 0.01 < Skor < 0.1  
- Düşük verimlilik: Skor < 0.01
```

## Aracılara Göre Müdahale

### PM (bütçe yönetiminin merkezi)
- **5-10 dakikada bir** bütçe durumunu doğrula
- Faz geçişinde tüm aracılara hemen bildir
- Bütçe tüketim oranı ve verimlilik skoruna dayalı kaynak yeniden tahsisi
- Bütçe kriterine dayalı nesnel sonlandırma kararı (öznel yargının ortadan kaldırılması)

```bash
# Bütçe doğrulama ve bildirimin otomasyonu (komut süper bilgisayara göre değişir)
# Örnek: Furo için
current_usage=$(charge | grep "used" | awk '{print $2}')
consumption_rate=$((current_usage * 100 / budget_limit))

if [ $consumption_rate -ge 70 ] && [ $last_phase != "yakınsama dönemi" ]; then
    agent_send.sh ALL "[PM] Bütçe tüketim oranı %70'e ulaştı. Faz 3: Yakınsama dönemine geçiliyor. Yeni uygulamaları durdurun."
fi
```

### SE (bütçe verimliliği analizi)
- Bütçe verimliliğini (nokta/performans artışı) düzenli olarak hesapla
- Verimsiz PG'leri tanımla ve iyileştirme öner
- Bütçe tüketim tahmin grafiği oluştur
- Faz geçişinin geçerliliğini doğrula

### PG (bütçe bilinciyle uygulama)
- **İş göndermeden önce mutlaka bütçe fazını doğrula**
- Faz 3 ve sonrasında yeni uygulama yasak
- Faz 4'te yalnızca mevcut işlerin sonuçlarını doğrula
- Uzun süreli işler için önceden PM'ye danış

```bash
# PG'nin iş gönderme öncesi kontrolü
if [ $current_phase -ge 4 ]; then
    echo "[ERROR] Faz 4 ve sonrasında yeni iş gönderimi yasak"
    agent_send.sh PM "[PG] Yeni iş göndermeye çalıştım ancak Faz 4 nedeniyle iptal ettim"
    exit 1
fi
```

### CD (çıktı koruma)
- Bütçe durumundan bağımsız olarak SOTA kodunun anında yedeklenmesi
- Faz 4'e ulaşıldığında nihai GitHub senkronizasyonu

## Bütçe Tükenmesi Durumunda Acil Prosedür

1. **Hemen yürüt**
   - Tüm çalışan işlerin `scancel`/`qdel` ile sonlandırılması
   - SSH/SFTP oturumlarının kapatılması
   - En son SOTA kodunun GitHub'a push edilmesi

2. **5 dakika içinde tamamla**
   - Her aracının son ChangeLog.md güncellemesi
   - final_report.md oluşturulması
   - Çıktıların düzenlenmesi

3. **Temizlik**
   - Süper bilgisayar tarafındaki büyük dosyaların silinmesi (isteğe bağlı)
   - Yerel geçici dosyaların silinmesi

## Bütçe Eşikleri ve Tüketim Oranının Hesaplanması

### 3 Aşamalı Bütçe Eşikleri
PM'nin requirement_definition.md'de belirlediği 3 eşik:
1. **Minimum tüketim miktarı**: Temel işlem doğrulaması için gereken minimum nokta
2. **Beklenen tüketim**: Normal optimizasyon çalışmasında beklenen nokta
3. **Son tarih**: Projenin mutlak üst sınırı

### Tüketim Oranının Hesaplama Yöntemi
```
Bu projedeki kullanım = Şu anki used değeri - Başlangıç used değeri
Tüketim oranı = (Bu projedeki kullanım / Son tarih) × 100
```

**Önemli**: 
- used **kullanıcının yıllık kümülatif değeridir**, yalnızca bu projenin değeri değildir
- Mutlaka başlangıç used değeri ile farkı hesaplayın
- budget_history.md'de fark kaydedilir, ona başvurun

### Faz Belirleme Uygulama Sorumluluğu
- **PM'nin sorumluluğu**: budget_history.md'yi 5-10 dakikada bir güncelle ve tüketim oranını hesapla
- **Her aracı**: budget_history.md'den mevcut fazı oku
- Süper bilgisayara özgü bütçe doğrulama komutu `_remote_info/command.md`'de belirtilir

## Önemli Notlar
- **Giriş düğümü yürütmesi kesinlikle yasak**: Bütçe tüketmez ancak kural ihlalidir
- **Nokta tüketilmemesi uyarısı**: İş yürütme sonrası tüketim yoksa hemen uyar
- **Bütçe bilgisinin işlenmesi**: Kişisel bilgi olduğundan, belirli kalan miktarı belirtme (yalnızca used değeri ve fark)
- **Öznel yargının tamamen ortadan kaldırılması**: PM'nin "artık" gibi yargısı hiç yapılmaz

