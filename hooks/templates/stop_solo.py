#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook for SOLO Agent
Tekli ajan için - zaman yönetimi ve devam görevleri bildirimi
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta


def find_project_root(start_path):
    """Proje kökünü (VibeCodeHPC-tr) bul"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def get_stop_count():
    """Geçerli dizindeki stop_count.txt dosyasından sayıyı al"""
    stop_count_file = Path.cwd() / ".claude" / "hooks" / "stop_count.txt"
    
    if stop_count_file.exists():
        try:
            return int(stop_count_file.read_text().strip())
        except:
            return 0
    return 0


def increment_stop_count():
    """stop_count.txt değerini artır"""
    hooks_dir = Path.cwd() / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    stop_count_file = hooks_dir / "stop_count.txt"
    current_count = get_stop_count()
    new_count = current_count + 1
    
    stop_count_file.write_text(str(new_count))
    return new_count


def get_elapsed_time():
    """Proje başlangıcından geçen süreyi al"""
    project_root = find_project_root(Path.cwd())
    if not project_root:
        return None
    
    start_time_file = project_root / "Agent-shared" / "project_start_time.txt"
    if not start_time_file.exists():
        return None
    
    try:
        start_time_str = start_time_file.read_text().strip()
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        current_time = datetime.now(start_time.tzinfo)
        elapsed = current_time - start_time
        return elapsed
    except:
        return None


def get_stop_threshold():
    """SOLO ajanı için STOP deneme eşiğini döndür"""
    project_root = find_project_root(Path.cwd())
    if project_root:
        threshold_file = project_root / "Agent-shared" / "stop_thresholds.json"
        if threshold_file.exists():
            try:
                with open(threshold_file, 'r') as f:
                    config = json.load(f)
                    thresholds = config.get('thresholds', {})
                    
                    if 'SOLO' in thresholds:
                        return thresholds['SOLO']
            except:
                pass
    
    return 100


def format_elapsed_time(elapsed):
    if not elapsed:
        return "bilinmiyor"
    
    total_seconds = int(elapsed.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours} saat {minutes} dakika"
    else:
        return f"{minutes} dakika"


def generate_block_reason(stop_count):
    """SOLO ajan için engelleme gerekçesini üret"""
    threshold = get_stop_threshold()
    elapsed = get_elapsed_time()
    elapsed_str = format_elapsed_time(elapsed)
    
    if stop_count >= threshold:
        reason = f"""
⚠️ STOP denemesi sayısı üst sınıra ulaştı (sınır: {threshold} kez)
Geçen süre: {elapsed_str}

📝 Önemli: Projeyi kapatacaksanız requirement_definition.md dosyasını yeniden gözden geçirin ve
   tüm gereksinimlerin madde madde karşılandığını ☑ doğrulayın.

SOLO ajanı olarak kapanış öncesi şu görevleri uygulayın:

1. [PM] Gereksinim kontrolü ve nihai değerlendirme:
   - requirement_definition.md içindeki tüm maddeleri kontrol edin
   - Elde edilen performans ile teorik performansı karşılaştırın
   - Bütçe kullanım durumunun son kontrolünü yapın

2. [PG] Çıktıların düzenlenmesi:
   - ChangeLog.md’yi son kez güncelleyin
   - SOTA başarım kodlarını doğrulayın
   - Çalışma dizinini düzenleyin

3. [SE] İstatistik ve görselleştirme (mümkün olduğu ölçüde):
   - SOTA eğilim grafiğini üretin
   - Nihai raporu oluşturun

4. [CD] GitHub senkronizasyonu (gerekiyorsa):
   - GitHub/dizine kopyalama
   - git commit

Ardından exit komutuyla çıkın.
"""
        return reason
    
    reason = f"""SOLO ajansınız (tekli mod). Bekleme durumuna geçmek izinli değildir.
[STOP denemesi: {stop_count}/{threshold}] [Geçen süre: {elapsed_str}]

[Zorunlu dosyaların yeniden gözden geçirilmesi]
Aşağıdaki dosyalardan güncel durumu kontrol edin (okunmamış olanları veya yalnızca 10 satır okunmuş olanları önceleyin):
- CLAUDE.md
- instructions/SOLO.md
- requirement_definition.md
- Agent-shared/directory_pane_map.txt
- Agent-shared/strategies/auto_tuning/typical_hpc_code.md
- Agent-shared/budget/budget_history.md
- Agent-shared/sota/sota_visualizer.py (SOTA görselleştirme zorunlu görev)
- telemetry/context_usage_monitor.py (kontekst izleme zorunlu görev)
- Agent-shared/ssh_sftp_guide.md (SSH/SFTP bağlantı/çalıştırma kılavuzu)
- hardware_info.md (teorik performans hedefi)
- Mevcut dizindeki ChangeLog.md

[Zorunlu asenkron görevler (öncelik sırasıyla)]
1. En yüksek öncelik: Konteks kullanım oranı görselleştirme (auto-compact önleme)
   python3 telemetry/context_usage_monitor.py --graph-type overview
   (Her 30 dakikada, 30/60/90/120/180 dakikalarda milestone kaydı)

2. Öncelik: SOTA performans grafiği (çıktıların görselleştirilmesi)
   for level in project family hardware local; do
       python3 Agent-shared/sota/sota_visualizer.py --level $level
   done

3. Normal: Bütçe eğilimi (mümkünse)
   python3 Agent-shared/budget/budget_tracker.py --graph

[Role göre devam görevleri]

[PG] Kod uygulama:
- Bir sonraki sürüm için optimizasyon uygulamaları
- İş sonuçlarının kontrolü (pjstat/pjstat2)
- Parametre ayarlamaları

[CD] GitHub sürekli senkronizasyon:
- SOTA başarım kodlarının düzenli commit edilmesi (tek seferlik değil)
- ChangeLog.md güncellemeleriyle senkron

En öncelikli görevi ToDo listesiyle yönetin ve uygulayın.
(Kalan STOP deneme hakkı: {threshold - stop_count} kez)
"""
    
    return reason


def main():
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id')
        stop_hook_active = input_data.get('stop_hook_active', False)
        
        stop_count = increment_stop_count()
        
        reason = generate_block_reason(stop_count)
        
        if reason:
            print(reason, file=sys.stderr)
            sys.exit(2)
        
        sys.exit(0)
        
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
