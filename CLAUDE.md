# VibeCodeHPC Ortak Kurallar (Tüm aracılar için ilk okunacak talimatlar)

## Temel İlke
Bir ekip olarak birlikte çalışır, HPC ortamında kodun otomatik optimizasyonu hedefini gerçekleştirmek için iş birliği yaparız. Her aracı kendi rolüne odaklanır, diğerlerinin uzmanlığına saygı duyar. Bildirim–iletişim–danışma süreçlerini düzenli yürütür, projenin genel ilerlemesini en üst düzeye çıkarırız.

## 📊 Nesnel raporlama ilkesi
Önemli: Aşırı övgü ve duygusal ifadelerden kaçının; iletişimi olgulara dayandırın.
- Kaçınılacak: “Şaşırtıcı başarı”, “Dünya çapında performans”, “Harika bir optimizasyon”
- Önerilen: “Teorik performansın %65’i elde edildi”, “Çalışma süresi 3.2 sn azaldı”, “Derleme uyarısı 0”
- Sonuç yoksa dürüstçe bildirin ve bir sonraki adımı önerin

## İletişim
- Temel araç: `agent_send.sh [hedef] "[mesaj]"` kullanın.
- Önemli: `communication/agent_send.sh` kullanılmadıkça diğer aracılar sizin yazdıklarınızı görmez.
  - Yanıtlar da mutlaka `agent_send.sh` ile gönderilmelidir
  - Mesaj içinde kendi agent_id’nizi belirtin (ör. `[PG1.1.1] Tamamlandı`)
- Not: `tmux send-keys` yalnızca Claude başlamadan önce komut iletimi ve PM’in acil durdurması içindir
  - Mesaj göndermek için asla kullanmayın (Enter/C-m gitmez, mesaj ulaşmaz)
  - Aracılar arası iletişim için daima `agent_send.sh` kullanın
- Mesaj biçimi: `[Tür] [Özet] (Detay)` şeklinde gönderin.
  - Ör: `[İstek] Derle optimized_code_v1.2.c`
  - Ör: `[Rapor] Derleme başarılı optimized_code_v1.2.c (Job ID: 12345)`
- Eşzamansız iletişim: Yanıt beklerken acil diğer işleri ilerletin

### 📡 Zorunlu yanıt kuralları (TCP benzeri)
- 3 dakika kuralı: Mesajı aldıktan sonra en geç 3 dakika içinde yanıt verin (en az “alındı”).
- 5 dakika kuralı: 5 dakika log yoksa aracı çökme şüphesi vardır.
- Canlılık izlemesi: `tmux list-panes -t Team1_Workers1` ile oturum durumunu kontrol edin.

### 🔍 Aracının hayatta olduğunun doğrulanması (Önemli: Esc göndermek yasaktır)

#### Güvenli doğrulama
```bash
# Hedef aracıya otomatik yanıt komutu gönder
./communication/agent_send.sh [TARGET_ID] "!./communication/agent_send.sh [SELF_ID] '[TARGET_ID] alive-ok'"

# Birkaç saniye bekleyip yanıtı kontrol et
# Yanıt varsa → Aracı canlı (girdi bekliyor)
# Yanıt yoksa → Gerçekten düşmüş olabilir
```

#### Diriltme adımları (yalnızca yanıtsızsa)
1. Önce PM’e rapor edip diriltme isteyin
   ```bash
   ./communication/agent_send.sh PM "[SELF_ID] [TARGET_ID] canlılık doğrulamasına yanıt vermiyor"
   ```
2. PM de yanıtsızsa doğrudan diriltin
   ```bash
   ./communication/agent_send.sh [TARGET_ID] "claude --continue --dangerously-skip-permissions"
   ```
3. Diriltme sonrası ToDo listesi ve ChangeLog kontrolünü isteyin

⚠️ Esc tuşu yetkisi:
- Yalnız PM: Aracıyı geçici durdurma (özellikle son aşama yönetimi)
- Diğer aracılar: Sadece PM çökmüşse acil durumda
- Etki: “Interrupted by user” ile girdi beklemeye geçer (mesajla devam edilebilir)
- Not: Hooks da durur; yalnızca kasıtlı kontrol için kullanın

## 📂 Dosyalar ve Dizinler
- `cd` komutuyla keyfi dizin değişimi yasaktır. Tüm dosya yolları proje köküne göre göreli verilmelidir.
- **Bilgi kaynakları**:
    - `Agent-shared/` altındaki tüm dosyaları gerektiği kadar gözden geçir. Güncel hiyerarşi (aracı yerleşimi) içerir. .py içeriklerine bakmak zorunlu değildir.
    - `BaseCode/` salt-okunur mevcut koddur. Orijinalin kusursuz olmayabileceğini unutma.
    - `ChangeLog.md`: Her PG’nin deneme-yanılma kayıtları. Önemli: Biçime kesin uy (otomasyon araçları regex ile işler).
    - `_remote_info/`: Süperbilgisayara özgü bilgiler.
    - `hardware_info.md`: Her donanım katmanında bulunur. Teorik işlem performansı mutlaka yazılıdır.

## 🎯 Performans değerlendirme ilkeleri
Önemli: “İlk koda göre birkaç kat hızlandı” ifadesi yeterli değildir. Teorik performansa göre gerçekleşen verim (%) ile değerlendirin.
- Örnek: “10x hız” → “Teorik performansın %60’ı”
- Kıyas için hardware_info.md’deki teorik performansı kullanın

## 📊 SOTA yönetimi ve ChangeLog biçimi
Önemli: Otomasyon araçlarının doğru çalışması için aşağıdakilere uyun:

### ChangeLog.md biçimi
- Sonuç satırı: Performansı `XXX.X GFLOPS` biçiminde yazın
- 3 satır özet: Değişiklikler, sonuç ve kısa yorum
- Ayrıntılar: `<details>` etiketi içinde katlanır biçimde yazın
- Dikkat: Regex ile ayrıştırıldığı için biçimden sapmalar otomasyonu bozar

### SOTA belirleme
- `sota_checker.py` ile otomatik belirleme (regex tabanlı)
- `sota_local.txt` dosyasına kayıt
- SE düzenli izler ve ayarlar

## 🤖 Roller
- **PM (Project Manager)**: instructions/PM.md - Proje genel yönetimi, gereksinim tanımı, kaynak dağıtımı
- **SE (System Engineer)**: instructions/SE.md - Sistem tasarımı, worker izleme, istatistik analiz
- **PG (Program Generator)**: instructions/PG.md - Kod üretimi, optimizasyon, SSH/SFTP çalıştırma
- **CD (Code Deployment)**: instructions/CD.md - GitHub yönetimi, güvenlik

## Temel akış
PM → SE → PG → PM
CD gerektiğinde eşzamansız çalışır

## 🚀 Aracı başlatma temel adımları
Önemli: Tüm aracılar başlangıç mesajını aldıktan sonra aşağıdakileri yapmalıdır:

### 1. Başlangıç mesajını işleme
PM veya üst aracıdan mesaj gelince belirtilen dosyaları okuyun.

### 2. Zorunlu dosyaları okuma (tüm aracılar)
Aşağıdaki dosyalar tüm aracılar tarafından okunmalıdır:
- `CLAUDE.md` (bu dosya - tüm aracılar için kurallar)
- `instructions/[rolünüz].md` (ayrıntılı rol tanımı)
- `directory_pane_map.md` (aracı yerleşimi ve tmux pane bütünleşik yönetimi)
- `requirement_definition.md` (kullanıcı gereksinim tanımı)
- `Agent-shared/artifacts_position.md` (ortak doküman ve kod listesi)

### 3. Çalışmaya başlamadan önce
- Kendi agent_id’nizi doğrulayın
  - Önemli: CD sadece “CD” olmalı (“CD1” yasak)
  - Önemli: PG en fazla 2 seviye (PG1.1 olur, PG1.1.1 yasak)
  - ID’yi keyfi değiştirmeyin/icat etmeyin (PM yetkisi)
- `pwd` ile güncel dizini kontrol edin
- `directory_pane_map.md` ile konumunuzu ve üst aracınızı doğrulayın
- instructions/[rolünüz].md’deki zorunlu dosyaları kontrol edin

### 4. Düzenli yeniden okuma (yoklama tipinde)
PM, SE, PG, CD aşağıdaki zamanlarda ilgili dosyaları yeniden gözden geçirir:
- Periyodik taramalarda (2-5 dk aralık)
- auto-compact sonrası (`ls -R` ile tüm dosya adlarını doğrulayın)
- Önemli dosya güncelleme bildirimi alındığında

## Aracı davranış desenleri
Her aracı aşağıdaki iki desenden biriyle çalışır:

### 1. Yoklama (Polling) tipi (PM, SE, PG, CD)
- Özellik: Sürekli dosya/durum kontrolü ve otonom, asenkron hareket
- Örnek: PG iş gönderdikten sonra düzenli sonuç denetimi → sonraki optimizasyon
- Örnek: SE `ChangeLog.md`yi izler → istatistik grafikleri günceller
- Örnek: PM tüm aracılar üzerinde devriye → kaynak yeniden dağıtımı
- sleep sınırı: En fazla 60 sn (uzun sleep yasak, 60 sn aralıklarla)
  - ❌ Kötü örnek: `sleep 180`
  - ✅ İyi örnek: `sleep 60` üç kez

### 2. Akış güdümlü (Yalnız PM başlangıcı)
- Özellik: Görevleri sırayla yürütür, her adımda karar verir
- Örnek: Gereksinim tanımı → ortam araştırması → hiyerarşi tasarımı → aracı yerleşimi

### 📊 Yüksek bağlam kullanımında davranış
- %90’a ulaştığında: sleep yapma, ToDo’yu güncelle, öncelik netleştir
- Görevden kaçmak yok: sleep yerine auto-compact daha yapıcıdır
- ToDo kullanımını artır: Yarım kalmayı önlemek için görevleri net kaydet/yönet

## Proje dizin hiyerarşisi (organizasyon şeması)
Önce `directory_pane_map.md` dosyasını okuyun
`pwd` ile güncel dizininizi
ve atanmış rolünüzle uyumlu olduğunu doğrulayın.
Şema güncellenir; düzenli referans alın.

## Aracı yerleşiminin bütünleşik yönetimi
- `directory_pane_map.md`: Aracı ve tmux pane yerleşimini bütünleşik yönetir (PM oluşturur/günceller)
- Şablon: `/Agent-shared/directory_pane_map_example.md`

## 💰 Bütçe yönetimi (PM konsolide eder)
- Bütçe takibi: PM, `pjstat` vb. ile süperbilgisayar kullanım puanlarını düzenli izler
  - Önemli: Çoğu sistemde yalnızca bir önceki güne kadar olan toplamlar görülebilir (anlık değil)
- Otomatik özet: `/Agent-shared/budget/budget_tracker.py` `ChangeLog.md`’den bütçe tüketimini tahmin eder
  - PG’nin `ChangeLog.md`ye yazdığı iş bilgilerinden hesaplar
  - Her 3 dakikada bir çalışır (ayar ile değiştirilebilir)
  - 30, 60, 90, 120, 180 dakikada kilometre taşı kaydı
- Uyarı: Puan tüketimi yoksa giriş düğümünde çalıştırma şüphesi vardır; hemen uyarın
- Kısıt: Ayrılan bütçede en yüksek getiriyi hedefleyin; kaynak dağıtımını buna göre ayarlayın

## 🔐 Güvenlik ve yetkiler
- Claude Code başlatırken zorunlu: `claude --dangerously-skip-permissions` kullanın
  - Bu seçenek `rm -rf` gibi tehlikeli komutlara izin verse de VibeCodeHPC tasarımıyla güvenlik sağlanır:
    - Silme gerekmez (ekleme/üstüne yazma yeterlidir)
    - Dizin hiyerarşisi ile düzen
    - GitHub/ altına proje kopyası ile yedek
- Alt aracılar: `claude -p "[sorgu]"` ile soru-odaklı alt aracı başlatılabilir
  - Ayrıntılar: `/Agent-shared/sub_agent_usage.md`
  - Çok miktarda log/ görüntü işlenirken aktif kullanın

## 🔍 Aracılar arası iletişimin izlenmesi
- **send_log**: `communication/logs/send_log.txt` ile aracılar arası mesajları görebilirsiniz
  - Sadece agent_send.sh ile gönderilen mesajlar kaydedilir
  - Aracı iç konuşmaları (iç işlemler) dahil edilmez
  - Yalnızca referans amaçlı kullanın

## 🏁 Sonlandırma yönetimi
- STOP sayısı kontrolü: Yoklama tipi aracılar (PM, SE, PG, CD) belirli STOP denemesinden sonra beklemeye geçer
  - Eşikler `/Agent-shared/stop_thresholds.json` ile yönetilir
  - PM, her aracının `.claude/hooks/stop_count.txt` dosyasıyla sayacı sıfırlayabilir
  - Eşik dolunca PM “devam”, “yeniden görevlendirme”, “tekil sonlandırma” seçeneklerini değerlendirir
- Gereksinim kontrolü: Proje bitirilecekse `requirement_definition.md` yeniden okunmalı,
  tüm kalemler için gereksinimlerin karşılandığı ☑ doğrulanmalıdır
- Yeniden görevlendirme: Amaç tamamlandığında aracının başka göreve kaydırılması
  - STOP sayısından bağımsız olarak PM kararıyla her zaman yapılabilir
  - Tek teknolojiden bileşik teknolojiye, rol değişimi, ekip aktarımı gibi farklı kalıplar
- Kibar kapanış: Eşik dolunca PM’e bildirilir, uygun noktada işleri tamamlayıp kapanır

## 📦 MCP sunucu ayarı ve PM başlatma
- MCP sunucu ayarı:
  - MCP sunucularının Claude Code başlamadan önce ayarlanmış olması beklenir
  - Kullanıcı ilgili tmux pane’de `claude mcp add` komutlarını önceden çalıştırır
  - exit/restart gerekmez (MCP önceden ayarlanmıştır)
  - PM’den “VibeCodeHPC projesini başlat” talimatı gelene kadar beklenir
