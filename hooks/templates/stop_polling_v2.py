#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook v2 (Polling tipi ajanlar için)
PM, SE, PG, CD bekleme durumunu engelleme - STOP sayısı kontrollü sürüm
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def find_project_root(start_path):
    """Proje kök dizinini (VibeCodeHPC-jp) bul"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def get_stop_count():
    """Geçerli dizindeki stop_count.txt'den sayıyı al"""
    stop_count_file = Path.cwd() / ".claude" / "hooks" / "stop_count.txt"
    
    if stop_count_file.exists():
        try:
            return int(stop_count_file.read_text().strip())
        except:
            return 0
    return 0


def increment_stop_count():
    """stop_count.txt değerini arttır"""
    hooks_dir = Path.cwd() / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    stop_count_file = hooks_dir / "stop_count.txt"
    current_count = get_stop_count()
    new_count = current_count + 1
    
    stop_count_file.write_text(str(new_count))
    return new_count


def get_agent_info_from_cwd():
    """Geçerli dizinden ajan bilgilerini al"""
    cwd = Path.cwd()
    project_root = find_project_root(cwd)
    
    if not project_root:
        return None
    
    # agent_id.txt'den doğrudan oku (session_start.py ile aynı yöntem)
    agent_id_file = Path.cwd() / ".claude" / "hooks" / "agent_id.txt"
    if agent_id_file.exists():
        agent_id = agent_id_file.read_text().strip()
        return {"agent_id": agent_id}
    
    try:
        relative_dir = str(cwd.relative_to(project_root))
        if relative_dir == ".":
            relative_dir = ""
    except ValueError:
        relative_dir = str(cwd)
    
    table_file = project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
    
    if table_file.exists():
        with open(table_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                entry = json.loads(line)
                if entry.get('working_dir') == relative_dir:
                    return entry
    
    return None


def get_stop_threshold(agent_id):
    """Ajan türüne göre STOP sayısı eşiğini döndür"""
    if not agent_id:
        return 30
    
    project_root = find_project_root(Path.cwd())
    if project_root:
        threshold_file = project_root / "Agent-shared" / "stop_thresholds.json"
        if threshold_file.exists():
            try:
                import json
                with open(threshold_file, 'r') as f:
                    config = json.load(f)
                    thresholds = config.get('thresholds', {})
                    
                    if agent_id in thresholds:
                        return thresholds[agent_id]
                    
                    for prefix in ['PM', 'CD', 'SE', 'PG']:
                        if agent_id.startswith(prefix) and prefix in thresholds:
                            return thresholds[prefix]
            except:
                pass
    
    if agent_id == "PM":
        return 50
    elif agent_id.startswith("CD"):
        return 40
    elif agent_id.startswith("SE"):
        return 30
    elif agent_id.startswith("PG"):
        return 20
    else:
        return 30  # Diğer ajanlar için varsayılan


def get_required_files(agent_id):
    """Ajan ID'sinden gerekli dosya listesini üret"""
    common_files = [
        "CLAUDE.md",
        "requirement_definition.md (kullanıcı niyetini anlama)",
        "Agent-shared/directory_pane_map.txt"
    ]
    
    role = agent_id.split('.')[0].rstrip('0123456789') if agent_id else ''
    
    role_files = {
        "PM": [
            "instructions/PM.md (ayrıntılı rol tanımı)", 
            "_remote_info/ (uzak sistem bağlantı bilgileri)", 
            "Agent-shared/max_agent_number.txt (kullanılabilir işçi sayısı)",
            "Agent-shared/agent_and_pane_id_table.jsonl (ajan çalışma durumu)",
            "Agent-shared/stop_thresholds.json (bitiş eşiği yönetimi)",
            "Agent-shared/artifacts_position.md (çıktı yerleşim kuralları)",
            "User-shared/visualizations/context_usage_*.png (auto-compact izleme)",
            "User-shared/reports/ (son rapor, yinelenmeyi önleme)"
        ],
        "SE": [
            "instructions/SE.md (ayrıntılı rol tanımı)", 
            "Agent-shared/report_hierarchy.md (rapor hiyerarşisi)",
            "Agent-shared/budget/budget_termination_criteria.md (bütçe bitiş koşulları)",
            "Agent-shared/compile_warning_workflow.md (PG desteği için)",
            "Agent-shared/sub_agent_usage.md (token tasarruf yöntemi)",
            "User-shared/visualizations/sota/project/ (güncel PNG kontrolü)",
            "Flow/ veya proje hiyerarşisindeki ChangeLog.md grubu (PG faaliyetlerinin takibi)"
        ],
        "PG": [
            "instructions/PG.md (ayrıntılı rol tanımı)", 
            "_remote_info/ (SSH bağlantı bilgileri, gerekirse)",
            "Agent-shared/strategies/auto_tuning/ (optimizasyon stratejileri)",
            "Agent-shared/compile_warning_workflow.md (uyarı işleme yöntemi)",
            "Agent-shared/artifacts_position.md (çıktı yerleşim kuralları)",
            "hardware_info.md (ilgili katman, kuramsal performans hedefi)", 
            "BaseCode/ (orijinal kod, göreli yol)",
            "../*/ChangeLog.md (diğer PG çıktıları, visible_path üzerinden)",
            "User-shared/visualizations/sota/family/ (kendi teknik alanın)"
        ],
        "CD": [
            "instructions/CD.md (ayrıntılı rol tanımı)", 
            "_remote_info/user_id.txt (anonimleştirme hedefi)",
            "Agent-shared/artifacts_position.md (çıktı yerleşimi; daha önce okunmuş olmalı)",
            "Her PG'nin ChangeLog.md dosyası (son güncellemeyi kontrol et)",
            "Her PG'nin sota_local.txt dosyası (SOTA doğrulaması)",
            "../Flow/ veya proje hiyerarşisindeki sota_*.txt (yeni SOTA tespiti)",
            "../.gitignore (GitHub/ altında olduğundan bir üstte)"
        ]
    }
    
    files = common_files.copy()
    if role in role_files:
        files.extend(role_files[role])
    
    return files


def generate_block_reason(agent_info, stop_count):
    """Polling tipi ajanlar için bloklama nedenini üret"""
    agent_id = agent_info.get('agent_id', 'unknown')
    threshold = get_stop_threshold(agent_id)
    
    if stop_count >= threshold:
        reason = f"""
⚠️ STOP deneme sayısı üst sınıra ({threshold} kez) ulaştı.

📝 Önemli: Proje kapatılacaksa requirement_definition.md yeniden gözden geçirilmeli ve
   tüm gereksinimlerin madde madde karşılandığı ☑ doğrulanmalıdır.

Ajan {agent_id} olarak aşağıdaki kapanış öncesi görevleri uygulayın:

1. PM'ye kapanış bildirimi:
   agent_send.sh PM "[{agent_id}] STOP sayısı üst sınıra ulaştı. Kapanış öncesi son görevler yürütülüyor."

2. Gereksinim kontrolü ve son görevlerin icrası:
   - requirement_definition.md içindeki tüm maddeleri kontrol et
   - Devam eden görevleri uygun bir noktada tamamla
   - ChangeLog.md'nin son güncellenmesi
   - Çalışma dizinini düzenle
   - Çıktıları doğrula

3. Nihai rapor:
   agent_send.sh PM "[{agent_id}] Kapanış hazırlığı tamam. Başlıca çıktılar: [buraya yaz]"

Sonrasında, PM'den gelecek agent.send ile kullanıcı yetkili “ESC” komutu ile zorla durdurma veya devam/yeniden görevlendirme talimatlarını beklemek için kısa beklemeler (örn. sleep) kullanın; bekleme süresini önce ~10 sn’den başlayıp kademeli artırın.
Birkaç dakika yanıt yoksa unutulmuş olabilir; PM ile yeniden iletişime geçin.

Not: ESC tuşu gönderilmiş bir ajan “kullanıcı tarafından kesildi” benzeri bekleme durumuna geçer. Bu ajana tekrar agent.send gelirse devam eder. PM iseniz, herkesin bittiğini doğrulamadan kendi bekleme oranınızı artırmayın; son kullanıcı onayını bekleyin.
"""
        return reason
    
    required_files = get_required_files(agent_id)
    
    reason = f"""Sen bir polling tipi ajansın ({agent_id}). Bekleme moduna geçmek izinli değildir.
[STOP denemesi: {stop_count}/{threshold}]

Proje yapısını kavrama:
Projenin genel resmi net değilse, önce aşağıdaki adımlarla yapıyı kontrol et:

1. Proje kökünü bul (cd kullanma):
   pwd ile konumunu doğrula, üst dizinleri göreli yollarla tara
   Örnek: /Flow/TypeII/single-node/OpenMP konumundayken:
   - ls ../../../../  ile kök katmanı kontrol et (CLAUDE.md ve Agent-shared olmalı)
   - ls ../../../../Agent-shared/  ile paylaşılan kaynakları kontrol et
   - Proje kökü genellikle VibeCodeHPC* adını taşır

2. Yapı doğrulaması (token tasarruf ederek):
   - ls ../  (aynı katmandaki diğer ajan/teknikleri gör)
   - ls -d ../../../*/  (yalnızca donanım katmanı dizinleri)
   - cat ../../../../Agent-shared/directory_pane_map.txt  (yerleşim haritası)
   - find . -name "*.md" -o -name "ChangeLog.md" | head -20  (önemli dosyalar)

3. Konum ve durumunu doğrula:
   - pwd  (tam yol)
   - ls -t . | head -10  (son güncellenen dosyalar)
   - ls -a .  (gizli dosyalar dahil; ancak -la yerine -a tercih et)

Zorunlu dosyaları yeniden gözden geçirme:
Aşağıdaki ölçütlerle önceliklendir:
1. Hiç okunmamış veya “üstünkörü okundu” (ör. yalnızca 10 satır) ise, fiilen okunmamış say
2. .md/.txt/.py (ana dokümanlar/scripter) öncelikli
3. ../../../../ ile başlayan göreli yollar proje kökü bazlıdır

Okunması gereken dosyalar:
{chr(10).join(f'- {file}' for file in required_files)}

Ardından aşağıdaki paralel görevleri yürüt:

"""
    
    # Görev bazlı paralel görevler (mevcut koddan)
    if "PM" in agent_id:
        reason += """[PM için paralel görevler]
1. Tüm aracılarda (SE, PG, CD) ilerleme kontrolü ve dolaşım
2. directory_pane_map.txt güncellemelerini doğrula
3. Bütçe yönetimi (pjstat ile puanları kontrol et)
4. Takılan aracılara müdahale
5. Kaynakların yeniden dağıtımını değerlendir

Özellikle son zamanlarda hiç kontrol edilmemiş aracıları önceliklendir.
"""
    
    elif agent_id.startswith("SE"):
        reason += """[SE için paralel görevler]
1. PG'lerin ChangeLog.md güncellemelerini izle
2. telemetry/context_usage_monitor.py ile bağlam kullanımını kontrol et
3. SOTA güncelleme geçmişi grafikleri üret (Agent-shared/log_analyzer.py)
4. İş yürütme sonuç bekleme durumlarını kontrol et
5. visible_path_PG*.txt dosyalarını güncelle
"""
    
    elif agent_id.startswith("PG"):
        reason += """[PG için paralel görevler]
1. ChangeLog.md güncellemesi ve SOTA yönetimi
2. SSH/SFTP oturum durumlarını kontrol et (Desktop Commander kullan)
3. İş kuyruğu durumunu kontrol et (squeue vb.)
4. Derleme uyarılarını analiz et ve düzelt
5. /results dizinini düzenle
6. Yeni optimizasyon yöntemlerini uygula

Performans artışı mümkün olduğu sürece iyileştirmeye devam et.
"""
    
    elif agent_id.startswith("CD"):
        reason += """[CD için paralel görevler]
1. PG'lerin SOTA'ya ulaşan kodlarını kontrol et
2. GitHub/dizin kopyalama ve anonimleştirme işlemleri
3. .gitignore güncellemelerini doğrula
4. git status ile değişiklikleri kontrol et
5. Commit mesajlarını hazırla

GitHub senkronizasyonunu eşzamanlı olmayan şekilde ilerlet.
"""
    
    reason += f"""
Yine de beklemek gerekiyorsa, sleep 10 vb. kullanın.
(Kalan STOP deneme hakkı: {threshold - stop_count})
"""
    
    return reason


def main():
    try:
        # JSON dosyasını yükle
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id')
        stop_hook_active = input_data.get('stop_hook_active', False)
        
        # Kendi ajan bilgilerini alır
        agent_info = get_agent_info_from_cwd()
        
        if agent_info:
            # STOP sayısını artırır
            stop_count = increment_stop_count()
            
            # Hata ayıklama günlüğü (gerekirse etkinleştir)
            # debug_log = Path.cwd() / ".claude" / "hooks" / "stop_debug.log"
            # with open(debug_log, 'a') as f:
            #     f.write(f"[{datetime.now()}] Stop #{stop_count}, agent={agent_info.get('agent_id')}\n")
            
            # Polling tipi ajanlar için durdurmayı engelle
            reason = generate_block_reason(agent_info, stop_count)
            
            if reason:
                # Çıkış kodu 2 ile stderr'ye çıktı verir
                print(reason, file=sys.stderr)
                sys.exit(2)
        
        # Normal sonlandırma
        sys.exit(0)
        
    except Exception:
        # Hatalar sessizce işlenir
        sys.exit(0)


if __name__ == "__main__":
    main()
