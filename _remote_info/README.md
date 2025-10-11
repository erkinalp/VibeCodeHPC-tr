# _remote_info Hiyerarşi Yapısı

Süper bilgisayara özgü bağlantı bilgileri ve proje ayarlarını saklayan dizindir.

⚠️ **Önemli**: Bu dizin Git yönetimi dışındadır.
Gizli bilgi içerdiğinden kesinlikle commit edilmemelidir.

## Klasör Yapısı Örneği

```
_remote_info/
├── flow/                   # Süper bilgisayar Furo durumunda
│   ├── user_info.md        # SSH bağlantı bilgileri ve uzak çalışma dizini
│   ├── command_list.md     # Sisteme özgü komut listesi
│   ├── sample_bash.sh      # İş betiği örneği
│   ├── load_custom_module.md  # Modül yükleme prosedürü
│   └── node_resource_groups.md  # 🆕 Kaynak grubu kısıtlama listesi (zorunlu)
│
└── fugaku/                 # Fugaku durumunda
    └── (benzer yapı)
```

## Zorunlu Ek Dosyalar

### `node_resource_groups.md` - Kaynak Grubu Kısıtlama Listesi
**Önemli**: Her süper bilgisayar dizinine mutlaka eklenmelidir.

#### Kayıt İçeriği
- Her kaynak grubu (iş sınıfı) ayrıntılı özelliklerini Markdown tablo formatında kaydet
- Aşağıdaki bilgileri içer:
  - Kaynak grubu adı (cx-small, fx-large vb.)
  - Minimum/maksimum düğüm sayısı
  - CPU/GPU çekirdek sayısı
  - Bellek kapasitesi
  - Maksimum yürütme süresi (varsayılan değer ve maksimum değer)
  - Ücret oranı (nokta/saniye)
  - Notlar (düğüm paylaşımı, öncelikli yürütme vb.)

#### Alma Yöntemi
1. Süper bilgisayarın resmi dokümantasyon sayfasından tabloyu kopyala
2. Markdown formatındaki tabloya dönüştür
3. Ücret hesaplama formülünü açıkça belirt (örnek: TypeII = 0.007 nokta/saniye×GPU sayısı)

#### Kullanım Amacı
- **PM**: Başlatmada okur, kaynak tahsis stratejisini belirler
- **PG**: İş gönderiminde uygun kaynak grubunu seçer
- **Bütçe yönetimi**: İş yürütme maliyetinin tahmin hesaplamasında kullanılır

## Dosya İçeriği Örnekleri

### `/flow/user_info.md`
```markdown
- **SSH bilgisi**: kullaniciadi@supercomputer.example.jp
- **SSH hedefinde kullanılan dizin**: /data/kullaniciadi/VibeCodeHPC/proje_adi/
```

### `/flow/command_list.md`
Sistemde kullanılabilir komutların listesi. Örnek:
- İş yönetimi: `pjsub`, `pjstat`, `pjdel`
- Bütçe doğrulama: `charge` (yol ayarı: `export PATH=/home/center/local/bin:${PATH}`)
- Ortam ayarı: `module avail`, `module load`

### `/flow/sample_bash.sh`
```bash
#!/bin/bash
#PJM -L rscgrp=cx-small      # Kaynak grubu belirtimi
#PJM -L node=2               # Düğüm sayısı
#PJM --mpi proc=8            # MPI işlem sayısı
#PJM -L elapse=1:00:00       # Yürütme süresi
#PJM -j                      # Standart hata çıktısını birleştir

module load oneapi
export OMP_NUM_THREADS=10
mpiexec -machinefile $PJM_O_NODEINF -n $PJM_MPI_PROC ./a.out
```

## Güvenlik Notları
- Dosya izinleri: `chmod 600` ile ayarla
- Parola ve özel anahtar🔑 harici ssh-agent ile yönet

