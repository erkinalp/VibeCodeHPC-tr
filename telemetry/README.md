# VibeCodeHPC Telemetri Sistemi

Bu dizin, aracılar için metrik toplama/görselleştirme ve OpenTelemetry yapılandırmasını yönetir.

## 📊 Özellikler

### 1. OpenTelemetry izleme
- Metrik ve logları OTLP (gRPC) protokolüyle dışa aktarır
- Aracı ID, takım ID ve çalışma dizinine göre etiketleme
- Grafana, LangFuse vb. arka uçlarda görselleştirme

### 2. Bağlam kullanım oranı izleme
- Her aracının kullandığı token sayısını takip (200.000 sınır)
- Otomatik sıkıştırma (auto-compact) olaylarını tespit ve kaydetme
- Zaman serisi grafikleri ile görselleştirme

### 3. Alt aracı istatistikleri
- `claude -p` kullanımını analiz eder
- Token tasarrufu etkisini nicelleştirir

## 🚀 Kullanım

### Aracı başlatma
```bash
# OpenTelemetry otomatik ayarlarıyla aracı başlat
./telemetry/launch_claude_with_env.sh PG1.1.1
```

Başlangıçta otomatik ayarlananlar:
- OpenTelemetry etkinleştirme (`otel_config.env.example` temel alınır)
- Aracı kimlik nitelikleri
- Alt aracı istatistikleri

### Yapılandırmayı özelleştirme

Uç nokta ve kimlik doğrulama bilgileri için `otel_config.env` dosyasını düzenleyin:
```bash
# Varsayılan yerel OTel Collector
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# LangFuse gibi harici hizmetler için
export OTEL_EXPORTER_OTLP_ENDPOINT=https://your-endpoint.com
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your-token"
```

## 📁 Dizin yapısı

```
telemetry/
├── otel_config.env.example    # OpenTelemetry yapılandırma şablonu  
├── docker-compose.yml         # Yerel test ortamı (Grafana + Prometheus)
├── sub_agent/                 # Alt aracı kullanım logları (claude_p_wrapper.sh üretir)
├── sub_agent_logs/            # Alt aracı istatistik logları (launch_claude_with_env.sh üretir)
└── visualization/             # Üretilen grafikler (analyze_sub_agent.py kullanır)
```

## 🔧 Arka uç ayarları

### Yerel geliştirme ortamı
```bash
# Docker Compose ile OTel Collector, Prometheus, Grafana’yı başlat
docker-compose -f telemetry/docker-compose.yml up -d

# Grafana erişimi
# http://localhost:3000 (admin/admin)
```

### Üretim ortamı
- Grafana Cloud
- LangFuse (OpenTelemetry izleme uyumlu)
- Datadog, New Relic gibi OTLP uyumlu servisler

## 📈 Görselleştirme araçları

### Bağlam kullanım izleme
```bash
# Ayrıntılı görselleştirme
python telemetry/context_usage_monitor.py

# Hızlı durum
python telemetry/context_usage_quick_status.py
```

### Alt aracı istatistikleri
```bash
python telemetry/analyze_sub_agent.py
```

### Bağlam kullanım durumu izleme
```bash
# Tüm aracıların durumunu görselleştir
python telemetry/context_usage_monitor.py

# Hızlı durum
python telemetry/context_usage_quick_status.py
```

## 📚 Kaynaklar

- Claude Code izleme dokümantasyonu: https://docs.anthropic.com/ja/docs/claude-code/monitoring-usage
- OpenTelemetry dokümantasyonu: https://opentelemetry.io/docs/
