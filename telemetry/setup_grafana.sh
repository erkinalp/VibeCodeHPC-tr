#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info() {
    echo -e "\033[1;32m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;34m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

show_usage() {
    cat << EOF
📊 VibeCodeHPC Grafana ortamı kurulumu

Kullanım:
  $0 [seçenekler]

Seçenekler:
  --check-only   : Sadece yapılandırmayı kontrol et (Docker başlatılmaz)
  --reset        : Mevcut konteynerleri silip yeniden oluştur
  --help         : Bu yardımı göster

Bu betik aşağıdakileri otomatik olarak yapar:
1. .env dosyasını doğrulama/oluşturma
2. Docker ortamını doğrulama
3. Grafana + Prometheus + OTel Collector’ı başlatma
4. Bağlantı bilgilerinin gösterimi

EOF
}

setup_env() {
    log_info "📝 OpenTelemetry yapılandırması kontrol ediliyor..."
    
    cd "$SCRIPT_DIR"
    
    if [ -f "otel_config.env" ]; then
        log_success "Mevcut otel_config.env kullanılacak"
    elif [ -f "otel_config.env.example" ]; then
        cp otel_config.env.example otel_config.env
        log_success "otel_config.env oluşturuldu"
    else
        log_error "otel_config.env.example bulunamadı"
        exit 1
    fi
    
    if grep -q "OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317" otel_config.env; then
        log_info "✅ Varsayılan yerel uç nokta ayarı doğrulandı"
    else
        log_info "⚠️  Özel bir uç nokta yapılandırılmış"
        grep "OTEL_EXPORTER_OTLP_ENDPOINT" otel_config.env || true
    fi
}

check_docker() {
    log_info "🐳 Docker ortamı kontrol ediliyor..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker kurulu değil"
        echo "Docker kurulum bilgisi: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon çalışmıyor"
        echo "Lütfen Docker Desktop’ı başlatın"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        log_error "Docker Compose kurulu değil"
        exit 1
    fi
    
    log_success "Docker ortamı doğrulaması tamamlandı"
}

start_grafana() {
    log_info "🚀 Grafana ortamı başlatılıyor..."
    
    cd "$SCRIPT_DIR"
    
    log_info "📥 Docker imajları indiriliyor..."
    if docker compose version &> /dev/null 2>&1; then
        docker compose pull
        docker compose up -d
    else
        docker-compose pull
        docker-compose up -d
    fi
    
    sleep 5
    
    if docker ps | grep -q "grafana"; then
        log_success "✅ Grafana ortamı başarıyla başlatıldı"
        echo ""
        echo "🐳 Çalışan konteynerler:"
        docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "(grafana|prometheus|otel)"
    else
        log_error "Grafana ortamı başlatılamadı"
        GRAFANA_CONTAINER=$(docker ps -a --format "{{.Names}}" | grep grafana | head -1)
        if [ -n "$GRAFANA_CONTAINER" ]; then
            docker logs "$GRAFANA_CONTAINER" 2>&1 | tail -20
        fi
        exit 1
    fi
}

show_connection_info() {
    echo ""
    echo "=================================================="
    echo "📊 VibeCodeHPC Grafana ortamı başlatıldı"
    echo "=================================================="
    echo ""
    echo "🌐 Erişim URL’leri:"
    echo "   Grafana: http://localhost:3000"
    
    if grep -qi microsoft /proc/version; then
        echo "   WSL ortamında: Windows tarafındaki tarayıcıdan erişin"
        if command -v ip &> /dev/null; then
            WSL_IP=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)
            echo "   veya: http://${WSL_IP}:3000"
        fi
    fi
    
    echo ""
    echo "🔐 Giriş bilgileri:"
    echo "   Kullanıcı adı: admin"
    echo "   Parola: admin"
    echo "   Not: İlk girişte parola değiştirmeniz istenir"
    echo ""
    echo "📡 Aracı bağlantı ayarları:"
    echo "   OTLP uç noktası: http://localhost:4317"
    echo ""
    echo "🔧 Konteyner yönetimi:"
    echo "   Durum kontrolü: docker ps"
    echo "   Günlükler: docker logs [KONTEYNER_ADI]"
    echo "   Durdur: cd $SCRIPT_DIR && docker compose down"
    echo ""
    echo "📈 Metrik kontrol adımları:"
    echo "   1. http://localhost:3000 adresine gidin"
    echo "   2. Sol menüden “Explore”’u seçin"
    echo "   3. “Prometheus” veri kaynağını seçin"
    echo "   4. Metrik adını girin (ör: agent_token_usage)"
    echo ""
}

reset_containers() {
    log_info "🔄 Mevcut konteynerler siliniyor..."
    
    cd "$SCRIPT_DIR"
    
    if docker compose version &> /dev/null 2>&1; then
        docker compose down -v
    else
        docker-compose down -v
    fi
    
    log_success "Mevcut konteynerler silindi"
}

main() {
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --check-only)
            setup_env
            check_docker
            log_success "Yapılandırma doğrulaması tamamlandı"
            exit 0
            ;;
        --reset)
            check_docker
            reset_containers
            setup_env
            start_grafana
            show_connection_info
            ;;
        "")
            setup_env
            check_docker
            start_grafana
            show_connection_info
            ;;
        *)
            log_error "Bilinmeyen seçenek: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
