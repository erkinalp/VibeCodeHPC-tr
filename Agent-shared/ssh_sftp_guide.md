# 🔌 SSH/SFTP Bağlantı ve Yürütme Kılavuzu (Desktop Commander MCP)

## Genel Bakış

PG/SE/PM aracılarının uzaktaki ortama SSH/SFTP ile bağlanıp komut çalıştırmaları ve dosya transferi yapmaları için bir kılavuzdur.
Desktop Commander MCP kullanılarak şunlar sağlanır:
- İki aşamalı kimlik doğrulamada tekrar gereksinimini azaltma (bir kez bağlanınca yeniden doğrulama gerekmez)
- Büyük dosya transferlerinde verimlilik
- Birden çok oturumun paralel yönetimi
- Aşırı standart çıktı kaynaklı bağlam israfının önlenmesi

## Ön Koşullar

### ssh-agent kurulumu (zorunlu)
Kullanıcı, `communication/setup.sh` çalıştırılmadan önce ayarlamalıdır.

### Desktop Commander MCP ön ayarı
```bash
# PM aracısı başlatılmadan önce yapılandırın
claude mcp add desktop-commander -- npx -y @wonderwhy-er/desktop-commander
```

## 🚀 En Hızlı Bağlantı Prosedürü

### 1. SSH Oturumu Kurma (Komut yürütme için)
Döndürülen PID'yi kaydedin (örnek: ssh_pid=37681)
```python
# Desktop Commander MCP ile bağlan
ssh_pid = mcp__desktop-commander__start_process(
    command="ssh -tt user@hostname",  # -tt ile PTY sağla
    timeout_ms=10000
)
```

### 2. SFTP Oturumu Kurma (Dosya transferi için)
Uygun kendi özel hiyerarşinizi doğrulayıp (ayırdıktan) sonra, SFTP oturumunu da kurun
```python
sftp_pid = mcp__desktop-commander__start_process(
    command="sftp user@hostname",
    timeout_ms=10000
)
# Döndürülen PID'yi kaydedin (örnek: sftp_pid=37682)
```

### 3. Komut Yürütme
interact_with_process ile komut yürütün
```python
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="cd /project/path && make",
    timeout_ms=30000
)
```

## 📁 Oturum Yönetimi

### Oturum Bilgilerinin Kaydı (Önemli)
Her aracı mutlaka mevcut dizinde `ssh_sftp_sessions.json` oluşturmalı ve yönetmelidir
```json
{
  "last_updated": "2025-01-30T12:34:56Z",
  "sessions": [
    {
      "type": "ssh",
      "pid": 37681,
      "host": "hpc.example.jp",
      "purpose": "main_commands",
      "created": "2025-01-30T10:23:45Z",
      "notes": "Ana komut yürütme için"
    },
    {
      "type": "sftp",
      "pid": 37682,
      "host": "hpc.example.jp",
      "purpose": "file_transfer",
      "created": "2025-01-30T10:25:12Z",
      "notes": "Dosya transferi özel"
    }
  ]
}
```

### Oturum Durumu Kontrolü
```python
# Periyodik olarak oturum durumunu kontrol et
mcp__desktop-commander__list_sessions()

# Belirli oturumun çıktısını kontrol et
mcp__desktop-commander__read_process_output(pid=ssh_pid, timeout_ms=1000)
```

## 🔄 Kullanım Alanına Göre Komut Örnekleri
Gerçek komutlar _remote_info altında sağlanan bilgiler ve SSH hedefinde doğrulanabilir (örnek betik) vb. referans alınmalıdır

### Derleme Yürütme
```python
# make çıktısını kaydederken yürüt
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="cd /project/path && make 2>&1 | tee compile_v1.2.3.log",
    timeout_ms=60000
)
```

### Toplu İş Gönderimi Örneği
```python
# İş betiği oluşturma
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="cat > job.sh << 'EOF'\n#!/bin/bash\n#SBATCH -N 1\n#SBATCH -t 00:10:00\n./program\nEOF",
    timeout_ms=5000
)

# İş gönderimi
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="sbatch job.sh",
    timeout_ms=5000
)

# İş durumu kontrolü
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="squeue -u $USER",
    timeout_ms=5000
)
```

### Dosya Transferi Örneği (SFTP Kullanımı)
```python
# Yükleme
mcp__desktop-commander__interact_with_process(
    pid=sftp_pid,
    input="put optimized_code.c",
    timeout_ms=30000
)

# İndirme
mcp__desktop-commander__interact_with_process(
    pid=sftp_pid,
    input="get job_12345.out",
    timeout_ms=30000
)

# Birden fazla dosya
mcp__desktop-commander__interact_with_process(
    pid=sftp_pid,
    input="mget *.log",
    timeout_ms=60000
)
```

### Ortam Araştırması (SE için - hardware_info.md oluşturma)
**Önemli**: Donanım bilgisi hesaplama düğümünde alınmalıdır.
Giriş düğümünden farklı CPU/GPU yapılandırması olabilir, bu nedenle mutlaka toplu iş veya etkileşimli iş ile hesaplama düğümüne girerek yürütün.

Ayrıntılar için `/Agent-shared/hardware_info_guide.md` dosyasına bakın.

```python
# Toplu iş betiği oluşturma
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="cat > hardware_check.sh << 'EOF'\n#!/bin/bash\n#SBATCH -N 1\n#SBATCH -t 00:05:00\nlscpu > hardware_info.txt\nnvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv >> hardware_info.txt 2>&1\nmodule avail 2>&1 | head -50 >> hardware_info.txt\nEOF",
    timeout_ms=5000
)

# İşi gönder ve hesaplama düğümünde yürüt
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="sbatch hardware_check.sh",
    timeout_ms=5000
)
```

## ⚠️ Hata İşleme ve Yedek Yöntem

### Desktop Commander Başarısız Olduğunda Çözüm
```python
# 1. MCP ile deneme (önerilen)
try:
    ssh_pid = mcp__desktop-commander__start_process(
        command="ssh -tt user@host",
        timeout_ms=10000
    )
except:
    # 2. Başarısız olursa standart Bash aracına geri dön
    Bash(command="ssh user@host 'cd /path && sbatch job.sh'")
    
    # 3. PM'ye rapor et
    agent_send.sh("PM", "[PG1.1.1] SSH yürütme başarısız: Desktop Commander MCP hatası. Bash yedek yöntemi kullanıldı")
```

### Oturum Kesildiğinde Yeniden Bağlanma
```python
# Oturum kesildiğinde
if session_disconnected:
    # ssh_sftp_sessions.json'dan eski PID'yi sil
    # Yeni oturum kur
    new_ssh_pid = mcp__desktop-commander__start_process(
        command="ssh -tt user@host",
        timeout_ms=10000
    )
    # ssh_sftp_sessions.json'ı güncelle
```

## 🎯 En İyi Uygulamalar

### 1. PID'nin Güvenilir Yönetimi
- Oturum oluşturulduğunda mutlaka `ssh_sftp_sessions.json`'ı güncelle
- Proje bitiminde tüm oturumları `force_terminate` ile sonlandır

### 2. Büyük Çıktı İle Başa Çıkma
```python
# Büyük çıktı bekleniyorsa dosyaya yönlendir
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="./large_output_program > output.txt 2>&1",
    timeout_ms=60000
)

# Sonra tail veya head ile yalnızca gerekli kısmı kontrol et
mcp__desktop-commander__interact_with_process(
    pid=ssh_pid,
    input="tail -n 100 output.txt",
    timeout_ms=5000
)
```

### 3. Dizin Yapısının Korunması
- Uzak ortamda da yerel ile aynı dizin hiyerarşisini koru
- Bu sayede makefile ve yapılandırma dosyası karışıklığı önlenir

## 📝 Çalışmazsa Kontrol Listesi
- [ ] ssh-agent ayarlanmış mı (kullanıcı tarafından önceden kurulum varsayılır)
- [ ] Desktop Commander MCP ayarlanmış mı (MCP dokümantasyonu yok)
- [ ] ssh_sftp_sessions.json ne zaman oluşturuldu kontrol et
- [ ] Bağlantı hedefi ve kullanıcının user_id'si _remote_info vb. ile sağlanan mı

## Özet

Desktop Commander MCP kullanarak verimli SSH/SFTP bağlantı yönetimi mümkün olur.
Her aracı (PG/SE/PM) gerektiğinde kendi oturumunu yönetir ve PID kaydıyla güvenilir kontrol sağlar.
