#!/bin/bash
# Kilometre taşı anlık görüntü oluşturma betiği

PROJECT_ROOT=$(pwd)
PYTHON_CMD="${PYTHON_CMD:-python3}"

# Proje başlangıç zamanını al
if [ -f "$PROJECT_ROOT/Agent-shared/project_start_time.txt" ]; then
    START_TIME=$(cat "$PROJECT_ROOT/Agent-shared/project_start_time.txt")
else
    echo "ERROR: project_start_time.txt not found"
    exit 1
fi

# ISO 8601 formatına dönüştür (gerekirse)
START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to parse start time: $START_TIME"
    exit 1
fi

echo "Proje başlangıç zamanı: $START_TIME"
echo "Kilometre taşı anlık görüntüleri oluşturuluyor..."

# Kilometre taşı zamanları (dakika)
MILESTONES=(30 60 90 120 180)

for MINUTES in "${MILESTONES[@]}"; do
    # Kilometre taşı zamanını hesapla
    MILESTONE_EPOCH=$((START_EPOCH + MINUTES * 60))
    MILESTONE_TIME=$(date -u -d "@$MILESTONE_EPOCH" +"%Y-%m-%dT%H:%M:%SZ")
    
    echo ""
    echo "=== ${MINUTES} dakika kilometre taşı ==="
    echo "Zaman: $MILESTONE_TIME"
    
    # Çıktı dosya adı
    OUTPUT_PATH="$PROJECT_ROOT/User-shared/visualizations/budget_usage_${MINUTES}min.png"
    
    # Grafik oluştur
    $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" \
        --graph \
        --as-of "$MILESTONE_TIME" \
        --output "$OUTPUT_PATH"
    
    # JSON raporu da oluştur
    REPORT_PATH="$PROJECT_ROOT/Agent-shared/budget/snapshots/milestone_${MINUTES}min.json"
    $PYTHON_CMD "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" \
        --json \
        --as-of "$MILESTONE_TIME" > "$REPORT_PATH"
    
    echo "Grafik: $OUTPUT_PATH"
    echo "Rapor: $REPORT_PATH"
done

echo ""
echo "Tüm kilometre taşı anlık görüntüleri oluşturma tamamlandı"

