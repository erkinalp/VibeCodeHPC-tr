#!/bin/bash

# Bu betik periyodik izleme gerçekleştirir.
# This script performs periodic monitoring.

LOG_FILE="/var/log/periodic_monitor.log"

# İzleme başlatılıyor...
echo "İzleme başlatılıyor..." >> $LOG_FILE # Monitoring starts

# Sistem yükünü kontrol et
LOAD=$(uptime | awk -F'load average: ' '{print $2}' | cut -d, -f1)

if (( $(echo "$LOAD > 5.0" | bc -l) )); then
    echo "Hata: Sistem aşırı yüklendi ($LOAD)" >> $LOG_FILE # Error: System load is high
    # Yöneticiye bildir
    # Notify administrator
    # send_alert "System load is high: $LOAD"
else
    echo "Sistem yükü normaldir ($LOAD)" >> $LOG_FILE # System load is normal
fi

# İzlemeyi sonlandırın.
echo "İzlemeyi sonlandırın." >> $LOG_FILE # Monitoring ends

# Tamamlama
# Complete

