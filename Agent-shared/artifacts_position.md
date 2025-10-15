# 📋 VibeCodeHPC Çıktı Yerleşim Kılavuzu

## Temel İlkeler
- ChangeLog.md merkezli tasarım: ilerleme bilgilerinin tek noktadan yönetimi
- Hiyerarşik yerleşimin netleştirilmesi: Agent-shared vs her aracının kendi dizini
- Yalnızca gerçekten var olan dosyaları listele

## Zorunlu Dokümanlar

### Proje kökünün hemen altında
```
VibeCodeHPC/
├── CLAUDE.md                    # Ortak kurallar (writer:PM, reader:all)
├── requirement_definition.md    # Proje gereksinimleri (writer:PM, reader:all)
├── directory_pane_map.md        # Aracı yerleşimi ve tmux pane yönetimi (writer:PM, reader:all)
├── sota_project.txt             # Project katmanı SOTA (writer:PG, reader:all)
├── GitHub/                      # CD yönetimi (writer:CD, reader:all)
│   └── [Anonimleştirilmiş proje kopyası]
└── User-shared/                 # Kullanıcıya yönelik çıktılar (writer:SE/PM, reader:User)
    ├── final_report.md          # Nihai rapor
    ├── reports/                 # Birleşik raporlar
    └── visualizations/          # Grafikler ve görseller
```

## Agent-shared katmanı

### Agent-shared/ (tüm aracılar tarafından görüntülenir)
```
Agent-shared/
├── change_log/                  # ChangeLog ile ilgili dosyalar
│   ├── ChangeLog_format.md      # Temel format tanımı (okuyucu:tümü)
│   ├── ChangeLog_format_PM_override_template.md # PM geçersiz kılma şablonu (yazar:PM, okuyucu:SE,PG)
│   ├── changelog_analysis_template.py # Analiz şablonu (yazar:SE, okuyucu:tümü)
│   └── changelog_helper.py      # ChangeLog kayıt yardımcısı (yazar:SE, okuyucu:PG,SE)
├── budget/                      # Bütçe yönetimi ile ilgili
│   ├── budget_termination_criteria.md # Bütçe tabanlı sonlandırma kriterleri (okuyucu:tümü)
│   ├── budget_tracker.py        # Bütçe toplama betiği (yazar:SE, okuyucu:PM,SE)
│   └── usage.md                 # Bütçe sistemi kullanım kılavuzu (okuyucu:PM,SE)
├── sota/                        # SOTA yönetimi ve görselleştirme
│   ├── sota_management.md       # SOTA yönetim sistemi özellikleri (okuyucu:tümü)
│   ├── sota_checker.py          # SOTA belirleme ve kayıt betiği (yazar:SE, okuyucu:tümü)
│   ├── sota_checker_usage.md    # SOTA belirleme aracı kullanımı (okuyucu:tümü)
│   ├── sota_visualizer.py       # SOTA görselleştirme aracı (yazar:SE, okuyucu:SE)
│   ├── sota_visualizer_usage.md # Görselleştirme aracı kullanımı (okuyucu:SE)
│   └── sota_grouping_config_template.yaml # Grup yapılandırma şablonu (yazar:SE, okuyucu:SE)
├── strategies/                  # Optimizasyon stratejileri
│   └── auto_tuning/
│       ├── typical_hpc_code.md  # HPC optimizasyonu tipik örnekleri (yazar:PM, okuyucu:tümü)
│       └── evolutional_flat_dir.md # Evrimsel arama stratejisi (yazar:PM, okuyucu:tümü)
├── directory_pane_map_example.md # Aracı yerleşim şablonu (okuyucu:PM)
├── hardware_info_guide.md       # Donanım bilgisi toplama kılavuzu (yazar:SE, okuyucu:tümü)
├── compile_warning_workflow.md  # Derleme uyarısı işleme akışı (okuyucu:PG)
├── ssh_sftp_guide.md            # SSH/SFTP bağlantı ve yürütme kılavuzu (okuyucu:PM,SE,PG)
├── sub_agent_usage.md           # Alt aracı kullanımı (okuyucu:tümü)
├── report_hierarchy.md          # Rapor hiyerarşi yapısı (okuyucu:SE)
├── PG_visible_dir_format.md     # PG başvuru izni formatı (okuyucu:SE,PG)
├── artifacts_position.md        # Çıktı yerleşim kuralları (bu dosya)
├── project_start_time.txt       # Proje başlangıç zamanı (yazar:PM, okuyucu:tümü)
├── agent_and_pane_id_table.jsonl # Aracı yönetim tablosu (yazar:PM,SE, okuyucu:tümü)
└── stop_thresholds.json         # STOP sayısı eşik ayarları (yazar:PM, okuyucu:tümü)
```

### _remote_info/ (süper bilgisayar ve kullanıcıya özgü)
```
_remote_info/
└── Flow/                        # Süper bilgisayara özgü ayarlar
    ├── command_list.md          # Yürütme komutları listesi
    ├── node_resource_groups.md  # Kaynak grubu tanımları
    ├── type2_compiler.md        # Derleyici bilgileri
    ├── user_info.md             # Kullanıcı ortam bilgileri (okuyucu:tümü, GitHub yayımında anonimleştirme zorunlu)
    └── sample_bash.sh           # Toplu iş betiği örneği (okuyucu:PG)
```

### communication/ (iletişim sistemi)
```
communication/
├── agent_send.sh                # Aracılar arası mesaj gönderimi
├── setup.sh                     # tmux oturumu oluşturma ve başlatma
├── start_agent.sh               # Aracı tekil başlatma
└── logs/
    └── send_log.txt             # Gönderim geçmişi (otomatik oluşturulur)
```

## Her Aracının Kendi Dizini

### Donanım katmanı dizini
```
Flow/TypeII/single-node/
├── hardware_info.md            # Donanım özellikleri (teorik hesaplama performansı dahil) (yazar:SE/PG, okuyucu:tümü)
├── sota_hardware.txt           # Hardware katmanı SOTA (yazar:PG, okuyucu:tümü)
├── intel2024/                  # Derleyici ortam katmanı
│   └── setup.md                # Ortam kurulum prosedürü (yazar:ilk PG, okuyucu:tüm PG'ler)
└── gcc11.3.0/                  # Derleyici ortam katmanı
    └── setup.md                # Ortam kurulum prosedürü (yazar:ilk PG, okuyucu:tüm PG'ler)
```

### PG Katmanı (paralelleştirme modülü)
```
OpenMP/ veya MPI/ vb. (PG'nin çalıştığı dizin)
├── ChangeLog.md                 # [ZORUNLU] Tüm bilgilerin birleştirilmesi (→Agent-shared/change_log/ChangeLog_format.md'ye bakın)
├── visible_path_PG1.1.txt       # Başvuru izni yol listesi (yazar:SE, okuyucu:PG) ※Yalnızca SE oluşturduğunda
├── sota_local.txt               # Local katmanı SOTA (yazar:PG, okuyucu:tümü)
├── optimized_code_v*.c          # Optimize edilmiş kod her sürüm (örn: matmul_v1.2.3.c)
├── batch_job_v*.sh              # Toplu iş betiği her sürüm
└── results/                     # Yürütme sonuç dosyaları (gerektiğinde oluşturulur)
    ├── job_12345.out
    └── job_12345.err
```

## Bilgi Birleştirme Yaklaşımı

### ChangeLog.md'de birleştirilen bilgiler
ChangeLog.md aşağıdaki tüm bilgileri merkezi olarak yönetir:
- **Sürüm geçmişi**: Her denemenin sürüm numarası (v1.0.0 formatı)
- **Değişiklik içeriği**: Uygulanan optimizasyon tekniklerinin açıklaması
- **Performans verileri**: GFLOPS, verimlilik, yürütme süresi
- **Derleme bilgileri**: Başarı/başarısızlık, uyarılar
- **İş bilgileri**: İş ID'si, yürütme durumu, kaynak kullanımı
- **SOTA başarı durumu**: local/family/hardware/project her katman

### Bağımsız dosya olarak yönetilen öğeler
- **Yürütme sonuç dosyaları**: Boyutu büyük (results/*.out, results/*.err)
- **Ortam kurulum prosedürleri**: Derleyici ortam katmanında paylaşılan (setup.md)
- **SOTA kayıtları**: Hızlı erişim için (sota_local.txt vb.)

## Alma ve Analiz Yöntemleri

### ChangeLog.md Analizi
```bash
# Sürüm listesini alma
grep "^### v" ChangeLog.md | sed 's/### //'

# En son performans verilerini alma (ilk performance satırı)
grep -m1 "performance:" ChangeLog.md

# İş ID listesini alma
grep "id:" ChangeLog.md | awk '{print $3}'

# SOTA başarısını doğrulama
grep "sota" ChangeLog.md -A1 | grep "scope:"
```

### SOTA Bilgisi Doğrulama
```bash
# Her katmandaki SOTA'yı doğrulama (dosya varsa)
cat sota_local.txt                           # PG dizini içinde
cat ../../../sota_hardware.txt               # Donanım katmanı
cat /path/to/project/sota_project.txt        # Proje kök dizini
```

### Python Araçlarının Kullanımı
```bash
# ChangeLog kayıt yardımcısı (PG için)
python3 /path/to/Agent-shared/change_log/changelog_helper.py \
  -v 1.0.0 -c "OpenMP paralelleştirme uygulaması" -m "İlk uygulama"

# SOTA görselleştirme (SE için)  
python3 /path/to/Agent-shared/sota/sota_visualizer.py --level project

# Bütçe toplama (PM için)
python3 /path/to/Agent-shared/budget/budget_tracker.py --summary
```

**Dikkat**: Yollar mutlak yol veya proje kök dizininden göreli yol olarak belirtilmelidir.
