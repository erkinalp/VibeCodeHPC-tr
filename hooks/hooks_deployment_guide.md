# VibeCodeHPC Claude Code Hooks Yerleştirme Kılavuzu (PM için)

## Genel Bakış
Claude Code hooks, aracının davranışlarını kontrol eden bir mekanizmadır. Özellikle:
- **Polling türü aracı (PM, SE, PG, CD)**: Bekleme durumunu engeller, sürekli aktif kalır
- **Tüm aracılar**: auto-compact sonrası gerekli dosyaların yeniden okunmasını teşvik eder

## Hooks sürümleri
v0.6.3 ve sonrasında, proje özelliklerine göre iki sürümden biri seçilebilir:

### v3 (varsayılan, önerilen)
- **Özellikler**: Dosya içeriğini olasılıksal olarak gömer, aracının özerkliğini vurgular
- **Ayar**: `Agent-shared/strategies/auto_tuning/auto_tuning_config.json` ile özelleştirilebilir
- **Kullanım**: Uzun soluklu projeler, auto-compact önlemleri, büyük ölçekli çok aracılı

### v2
- **Özellikler**: Yalnızca dosya yollarını sağlar, hafif çalışır
- **Kullanım**: Kısa süreli projeler, deneysel değerlendirme, küçük projeler

### Sürüm seçimi
```bash
# v3 kullan (varsayılan)
./communication/setup.sh 12

# v2 kullan
./communication/setup.sh 12 --hooks v2
```

## Otomatik yerleştirme (önerilen)

### start_agent.sh ile yerleştirme
```bash
# Varsayılan (hooks ve telemetry her ikisi de etkin)
./communication/start_agent.sh PG1.1.1 /Flow/TypeII/single-node/intel2024/OpenMP

# Yalnızca hooks devre dışı
VIBECODE_ENABLE_HOOKS=false ./communication/start_agent.sh PG1.1.1 /path/to/dir

# Yalnızca telemetry devre dışı
VIBECODE_ENABLE_TELEMETRY=false ./communication/start_agent.sh PG1.1.1 /path/to/dir

# Her ikisi de devre dışı (hafif mod)
VIBECODE_ENABLE_HOOKS=false VIBECODE_ENABLE_TELEMETRY=false ./communication/start_agent.sh PG1.1.1 /path/to/dir
```

## Manuel yerleştirme (sorun giderme)

### 1. Bireysel aracıya yerleştirme
```bash
# Aracı tipini kontrol et
# PM, SE, PG, CD → polling

# kancaları yerleştir
./hooks/setup_agent_hooks.sh SE1 /path/to/SE1/workdir polling
./hooks/setup_agent_hooks.sh PG1.1.1 /path/to/PG1.1.1/workdir polling
```

### 2. Yerleştirilen dosyalar
Her aracının çalışma dizinine aşağıdakiler yerleştirilir:
```
{AGENT_DIR}/
└── .claude/
    ├── hooks/
    │   ├── session_start.py  # Oturum başlangıcındaki işlem
    │   └── stop.py          # Bekleme sırasındaki işlem (türe göre)
    └── settings.local.json  # kancaları etkinleştirme ayarı
```

## Aracı türüne göre davranış

### Yoklama tipi (PM, SE, PG, CD)
- **Stop hook**: beklemeyi engeller, periyodik görev listesini sunar
- **SessionStart hook**: yeni başlatmada gerekli dosyalar listesini sunar
- **Önerilen dolaşım aralığı**:
  - PM: 2-5 dk (genel izleme)
  - SE: 3-10 dk (ilerleme izleme, iş süresine göre ayarla)
  - PG: 1-3 dk (iş yürütme sonucu kontrolü)
  - CD: eşzamansız (GitHub senkronizasyonu)

## session_id takibi

### agent_and_pane_id_table.jsonl güncellemesi
Claude başladıktan sonra, SessionStart kancası otomatik olarak şunları yapar:
1. session_id’yi kaydeder
2. Aracının durumunu "running" olarak günceller
3. Çalışma dizinini (cwd) kaydeder

```jsonl
{"agent_id": "PG1.1.1", "tmux_session": "Team1_Workers1", "tmux_window": 0, "tmux_pane": 3, "claude_session_id": "abc123...", "status": "running", "cwd": "/VibeCodeHPC-jp/Flow/...", "last_updated": "2025-08-02T12:34:56Z"}
```

## Sorun giderme

### hooks çalışmıyorsa
1. `.claude/hooks/` dizininin varlığını kontrol et
2. Python betiklerinin çalıştırma iznini kontrol et
3. `settings.local.json` içinde kancaların etkinleştirildiğini kontrol et
4. Python3’ün kullanılabilirliğini kontrol et

### Aracı sık sık duruyorsa
1. stop hook içindeki `stop_hook_active` kontrolünün düzgün çalıştığını doğrula
2. Aracı türü tespitinin doğru olduğunu doğrula
3. Gerekirse geçici olarak `VIBECODE_ENABLE_HOOKS=false` ile devre dışı bırak

### session_id kaydedilmiyorsa
1. `TMUX_PANE` ortam değişkeninin varlığını kontrol et
2. agent_and_pane_id_table.jsonl için yazma iznini kontrol et
3. tmux pane numarası ile tablonun tutarlılığını kontrol et

## Dikkat

1. **Kanca yerleştirme zamanlaması**: Claude başlatılmadan önce yerleştirilmelidir
2. **Mevcut kancalar**: Zaten varsa üzerine yazılır
3. **Projeye özgü ayarlar**: Her aracı bağımsız kanca ayarlarına sahiptir
4. **auto-compact önlemi**: Bağlam kullanım oranı %95 civarında özellikle önemlidir

## Gelişmiş ayarlar

### Özel kancalar ekleme
`hooks/templates/` içine özel kancalar ekleyip setup_agent_hooks.sh’i düzenleyerek projeye özgü kancalar yerleştirebilirsiniz.

### ⚠️ kancaları devre dışı bırakma (önerilmez)

**Önemli**: Kancaları devre dışı bırakmak kesinlikle önerilmez. Yoklama tipi aracılar (PM, SE, PG, CD) bekleme durumuna geçer ve proje durur.

Mutlaka devre dışı bırakmak gerekiyorsa:
1. **Proje başlamadan önce** ortam değişkenini ayarla
2. Tüm aracılara etki edeceğini anla
3. MCP sunucu ayarı ve `.claude/settings.local.json` dosyasının manuel yönetimi gerekir

```bash
# Yalnızca proje başlamadan önce (önerilmez)
export VIBECODE_ENABLE_HOOKS=false
```

**Öneri**: Kanca işlevini her zaman etkin kullanın.

## Başvuru Kaynakları
- Claude Code hooks resmi dokümantasyonu
- `hooks/templates/` içindeki betikler
- `telemetry/README.md` (telemetry ile entegrasyon)
