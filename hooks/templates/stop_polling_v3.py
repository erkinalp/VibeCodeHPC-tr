#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook v3 for Polling Agents
Dosya içeriğinin doğrudan gömülmesi ve akıllı seçim
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def find_project_root(start_path):
    """Proje kök dizinini bul"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


def get_stop_count():
    """TODO: Add docstring"""
    stop_count_file = Path.cwd() / ".claude" / "hooks" / "stop_count.txt"
    
    if stop_count_file.exists():
        try:
            return int(stop_count_file.read_text().strip())
        except:
            return 0
    return 0


def increment_stop_count():
    """TODO: Add docstring"""
    hooks_dir = Path.cwd() / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    stop_count_file = hooks_dir / "stop_count.txt"
    current_count = get_stop_count()
    new_count = current_count + 1
    
    stop_count_file.write_text(str(new_count))
    return new_count


def get_agent_info_from_cwd():
    """TODO: Add docstring"""
    # agent_id.txt’den doğrudan oku
    agent_id_file = Path.cwd() / ".claude" / "hooks" / "agent_id.txt"
    if agent_id_file.exists():
        agent_id = agent_id_file.read_text().strip()
        return {"agent_id": agent_id}
    
    cwd = Path.cwd()
    project_root = find_project_root(cwd)
    
    if not project_root:
        return None
    
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
    """TODO: Add docstring"""
    if not agent_id:
        return 30
    
    project_root = find_project_root(Path.cwd())
    if project_root:
        threshold_file = project_root / "Agent-shared" / "stop_thresholds.json"
        if threshold_file.exists():
            try:
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
    elif agent_id == "SOLO":
        return 100
    elif agent_id.startswith("CD"):
        return 40
    elif agent_id.startswith("SE"):
        return 30
    elif agent_id.startswith("PG"):
        return 20
    else:
        return 30


def load_config(project_root):
    """TODO: Add docstring"""
    config_file = project_root / "Agent-shared" / "strategies" / "auto_tuning" / "auto_tuning_config.json"
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return {
        "file_provision": {
            "always_full": [
                "requirement_definition.md",
                "Agent-shared/directory_pane_map.md",
                "CLAUDE.md"
            ],
            "periodic_full": [
                {"file": "instructions/{role}.md", "probability": 0.85},
                {"file": "ChangeLog.md", "probability": 0.75}
            ],
            "path_only": ["BaseCode/", "Agent-shared/strategies/"]
        },
        "agent_tasks": {}
    }


def should_provide_file(file_config, stop_count):
    """TODO: Add docstring"""
    if isinstance(file_config, str):
        # always_full ise
        return True
    
    file_path = file_config.get("file", "")
    probability = file_config.get("probability", 0.5)
    
    numerator = int(probability * 100)
    denominator = 100
    
    hash_offset = hash(file_path) % denominator
    
    return ((stop_count + hash_offset) % denominator) < numerator


def read_file_content(file_path, project_root, latest_entries=None):
    """TODO: Add docstring"""
    full_path = project_root / file_path
    
    if not full_path.exists():
        return None
    
    try:
        content = full_path.read_text(encoding='utf-8')
        
        # ChangeLog.md için özel işlem (yalnızca en yeni girdiler)
        if file_path.endswith('ChangeLog.md') and latest_entries:
            entries = content.split('### v')
            if len(entries) > 1:
                recent = '### v' + '### v'.join(entries[1:min(latest_entries + 1, len(entries))])
                return recent[:10000]  # ChangeLog sınırını gevşet
        
        if len(content) > 10000:
            return content[:10000] + "\n\n...[Dosya çok büyük olduğu için devamı kısaltıldı]"
        
        return content
    except Exception as e:
        return f"[Okuma hatası: {str(e)}]"


def resolve_file_path(file_path, project_root, agent_working_dir, fallback_paths=None):
    """TODO: Add docstring"""
    if file_path.startswith("./"):
        resolved = agent_working_dir / file_path[2:]
        if resolved.exists():
            return resolved
        return project_root / file_path[2:]
    
    if file_path.startswith("../"):
        resolved = agent_working_dir / file_path
        if resolved.exists():
            return resolved
    
    # fallback_paths varsa sırayla dene
    if fallback_paths:
        for fallback in fallback_paths:
            if fallback.startswith("../"):
                candidate = agent_working_dir / fallback
            else:
                candidate = project_root / fallback
            if candidate.exists():
                return candidate
    
    return project_root / file_path


def generate_embedded_content(stop_count, threshold, agent_id, project_root):
    """TODO: Add docstring"""
    config = load_config(project_root)
    
    role = agent_id if agent_id == "SOLO" else (agent_id.split('.')[0] if '.' in agent_id else agent_id)
    
    agent_working_dir = Path.cwd()
    
    embedded_parts = []
    reference_parts = []
    
    embedded_parts.append("## 📄 Zorunlu dosya içerikleri\n")
    for file_path in config["file_provision"]["always_full"]:
        formatted_path = file_path.replace("{role}", role)
        content = read_file_content(formatted_path, project_root)
        if content:
            embedded_parts.append(f"### {formatted_path}")
            embedded_parts.append("```")
            embedded_parts.append(content)
            embedded_parts.append("```\n")
    
    provided_any = False
    common_full = config["file_provision"].get("common_full", [])
    for file_config in common_full:
        if should_provide_file(file_config, stop_count):
            formatted_path = file_config["file"].replace("{role}", role)
            content = read_file_content(formatted_path, project_root)
            if content:
                if not provided_any:
                    embedded_parts.append("\n## 📋 Ek sağlanan dosyalar\n")
                    provided_any = True
                embedded_parts.append(f"### {formatted_path}")
                embedded_parts.append("```")
                embedded_parts.append(content)
                embedded_parts.append("```\n")
    
    # 3. periodic_full (Yeni yapı: Dosya odaklı)
    periodic_full = config["file_provision"].get("periodic_full", {})
    
    for file_path, file_config in periodic_full.items():
        # Bu rolün olasılığını alır
        probabilities = file_config.get("probabilities", {})
        if role not in probabilities:
            continue
        
        probability = probabilities[role]
        
        # Olasılık değerlendirmesi için config nesnesi oluşturma
        check_config = {"file": file_path, "probability": probability}
        
        if should_provide_file(check_config, stop_count):
            # Yolu çözümle
            formatted_path = file_path.replace("{role}", role)
            fallback_paths = file_config.get("fallback_paths")
            resolved_path = resolve_file_path(formatted_path, project_root, agent_working_dir, fallback_paths)
            
            # Joker karakter işlemi
            if file_config.get("type") == "wildcard":
                # Wildcard desenini glob ile işleme
                import glob
                pattern_path = str(project_root / formatted_path.lstrip('/'))
                matched_files = glob.glob(pattern_path)
                
                if matched_files:
                    for matched_file in matched_files[:10]:  # En fazla 10 dosyaya kadar (deney öncelikli)
                        file_path_obj = Path(matched_file)
                        if file_path_obj.exists():
                            try:
                                with open(file_path_obj, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Karakter sınırlaması yok (deney öncelikli)
                                    if content:
                                        if not provided_any:
                                            embedded_parts.append("\n## 📋 Ek sağlanan dosyalar\n")
                                            provided_any = True
                                        # Proje kökünden göreli yol gösterimi
                                        rel_path = file_path_obj.relative_to(project_root)
                                        embedded_parts.append(f"### {rel_path}")
                                        embedded_parts.append("```")
                                        embedded_parts.append(content)
                                        embedded_parts.append("```\n")
                            except Exception:
                                pass
            # Dizin listelemenin özel işlemi
            elif file_config.get("type") == "directory_listing":
                if resolved_path and resolved_path.exists() and resolved_path.is_dir():
                    if not provided_any:
                        embedded_parts.append("\n## 📋 Ek sağlanan dosyalar\n")
                        provided_any = True
                    embedded_parts.append(f"### {formatted_path} (Dizin listesi)")
                    embedded_parts.append("```")
                    try:
                        import os
                        for item in sorted(os.listdir(resolved_path)):
                            item_path = resolved_path / item
                            if item_path.is_dir():
                                embedded_parts.append(f"📁 {item}/")
                            else:
                                embedded_parts.append(f"📄 {item}")
                    except Exception as e:
                        embedded_parts.append(f"[Hata: {str(e)}]")
                    embedded_parts.append("```\n")
            else:
                # Normal dosya işlemleri
                latest_entries = file_config.get("latest_entries")
                # read_file_content, içinde çözülmüş (resolve edilmiş) bir yolu bekler
                if resolved_path and resolved_path.exists():
                    try:
                        with open(resolved_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # ChangeLog.md için özel işlem
                            if formatted_path.endswith('ChangeLog.md') and latest_entries:
                                entries = content.split('### v')
                                if len(entries) > 1:
                                    recent = '### v' + '### v'.join(entries[1:min(latest_entries + 1, len(entries))])
                                    content = recent[:10000]  # Gevşetilmiş kısıtlama
                            
                            if content:
                                if not provided_any:
                                    embedded_parts.append("\n## 📋 Ek sağlanan dosyalar\n")
                                    provided_any = True
                                embedded_parts.append(f"### {formatted_path}")
                                embedded_parts.append("```")
                                embedded_parts.append(content)
                                embedded_parts.append("```\n")
                    except Exception:
                        pass  # Dosya mevcut değilse sessizce atla
        else:
            # Sağlanmazsa yol referansı kullanılır
            reference_parts.append(file_path.replace("{role}", role))
    
    # 4. rare_full (düşük frekans)
    rare_full = config["file_provision"].get("rare_full", {})
    for file_path, file_config in rare_full.items():
        probabilities = file_config.get("probabilities", {})
        if role not in probabilities:
            continue
        
        probability = probabilities[role]
        check_config = {"file": file_path, "probability": probability}
        
        if should_provide_file(check_config, stop_count):
            formatted_path = file_path.replace("{role}", role)
            latest_entries = file_config.get("latest_entries")
            content = read_file_content(formatted_path, project_root, latest_entries)
            if content:
                if not provided_any:
                    embedded_parts.append("\n## 📋 Ek sağlanan dosyalar\n")
                    provided_any = True
                embedded_parts.append(f"### {formatted_path}")
                embedded_parts.append("```")
                embedded_parts.append(content)
                embedded_parts.append("```\n")
        else:
            reference_parts.append(file_path.replace("{role}", role))
    
    if reference_parts:
        embedded_parts.append("\n## 📁 Başvurulması önerilen dosyalar (gerektikçe okuyun)\n")
        for path in reference_parts:
            embedded_parts.append(f"- {path}")
    
    # 5. Bellek sıfırlama olasılığını ima eder
    if stop_count % 10 == 0:  # Her 10 seferde bir
        embedded_parts.append(f"\n{config['file_provision'].get('compact_recovery_hint', '')}")
    
    return '\n'.join(embedded_parts)


def get_agent_tasks(agent_id, config):
    """Her ajan için görev listesini al"""
    role = agent_id.split('.')[0] if '.' in agent_id else agent_id
    tasks = config.get("agent_tasks", {}).get(role, [])
    
    if not tasks:
        return ""
    
    task_list = "\n## 📌 Zorunlu Görevler (Hepsi Kontrol Edildi)\n"
    for i, task in enumerate(tasks, 1):
        task_list += f"{i}. {task}\n"
    
    return task_list


def generate_block_reason(stop_count, agent_info):
    """Blok nedenini oluşturur"""
    agent_id = agent_info.get('agent_id', 'unknown')
    threshold = get_stop_threshold(agent_id)
    project_root = find_project_root(Path.cwd())
    
    if not project_root:
        return "Proje kök dizini bulunamadı."
    
    config = load_config(project_root)
    
    # Eşik değere ulaşıldığında yapılacak işlemler
    if stop_count >= threshold:
        # Role göre çıkış hazırlık görevleri
        role_specific_tasks = {
            "PG": ["Mevcut işin tamamlanmasını bekleme", "ChangeLog.md son güncelleme", "Sonuç dosyalarının düzenlenmesi"],
            "SE": ["Devam eden analizin tamamlanması", "Son grafik güncelleme", "Rapor güncelleme"],
            "PM": ["Tüm ajanların durumunu kontrol etme", "final_report.md hazırlama", "Bütçe son kontrolü"],
            "CD": ["Son commit (yasak değilse push)", "GitHub senkronizasyonu tamamlandı", "Anonimleştirme son kontrolü"],
        }
        
        role = agent_id.split('.')[0] if '.' in agent_id else agent_id
        tasks = role_specific_tasks.get(role, ["Mevcut görevi tamamlama"])
        
        task_list = "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks)])
        
        return f"""
⚠️ STOP sayısı üst sınıra ({threshold} kez) ulaştı.

[Sonlandırma hazırlığı]
{task_list}

Son rapor:
agent_send.sh PM "[{agent_id}] Sonlandırma hazırlığı tamamlandı. Ana başarılar: [başarıları buraya yazın]"

PM'e önemli istek:
agent_send.sh PM "[{agent_id}] İşlemi durdurmak için, tmux send-keys -t [ilgili panel] Escape ile ESC tuşunu gönderin"

Ardından PM'den talimat (ESC zorla durdurma/devam/transfer) bekleyin.
sleep 20 vb. çalıştırın → durmadan ek iş olup olmadığını kontrol edin → düzenli olarak PM'e durum bildirin ... tekrarlayın.
"""
    
    # Normal blok
    reason = f"""Siz bir polling tipi ajanısınız ({agent_id}). Bekleme moduna geçmeniz izinli değildir.
[STOP denemesi: {stop_count}/{threshold}]

## Durdurma Yöntemi Rehberi (her seferinde gösterilir)
Kendi kendinize tamamen duramazsınız. Gerekirse aşağıdaki adımları izleyin:

1. **PM’ye durdurma talebi (önerilir)**:
   agent_send.sh PM "[{agent_id}] geçici duraklama gerekiyor. tmux send-keys -t [ilgili pane] Escape ile ESC tuşu gönderin"
   
2. **PM yanıt vermezse son çare**:
   - Yukarıdaki işlemi 3 defa veya daha fazla denediğiniz halde PM’den yanıt alamazsanız (PM önceden kapanmış olabilir)
   - Kendi çözüm adımları:
     1. Geçerli dizindeki `.claude/settings.local.json` dosyasını kontrol edin
     2. "hooks" bölümünden stop ile ilgili ayarları silin veya yorum satırı haline getirin
     3. Ayrıntılı yol ve ayar yöntemi için `/hooks/setup_agent_hooks.sh` dosyasına bakın
   
   ※Not: Kendi çözümünüz son çaredir. Öncelikle PM ile iletişime 3 defadan fazla geçmeye çalışın.

"""
    
    # Gömülü içeriği ekle
    reason += generate_embedded_content(stop_count, threshold, agent_id, project_root)
    
    # Ajan görevini ekle
    reason += get_agent_tasks(agent_id, config)
    
    # İletişim yönteminin hatırlatıcısı
    reason += f"""

## 🔄 Sonraki işlem
1. Yukarıdaki dosya içeriğini kontrol edin
  1.1. Sağlanan dosya yollarını aktif olarak referans alın
  1.2. Ham metin istemlerinin çoğu olasılıksal olarak sağlandığından, hatırlatıcı olarak etkili kullanın
  1.3. Dosyada yazılı yolları özyinelemeli olarak referans alın

Ancak geçerli dizine dikkat edin.
VibeCodeHPC-xxx gibi proje kök dizinini göreceli yol ile anlayın

2. Bu içerikleri dikkate alarak ToDo'yu güncelleyin
  2.1. Üzerinde çalışılan görevi düzenleyin
  2.2. Mevcut görevle doğrudan ilgili olmasa bile 'daha sonra yapılacak görevleri' unutmamak için ekleyin
  2.3. {{Eylem 1'de elde edilen yolu}} OKUMA... gibi şeyleri ToDo'ya eklemek de etkilidir

3. Yüksek öncelikli görevi seçin
4. Yürütmeyi başlatın
5. İlerleme varsa agent_send.sh ile rapor edin

1~5 tekrarlayın

[ÖNEMLİ] agent_send.sh kullanım yöntemi:
Proje kök dizininden göreceli veya mutlak yol ile belirtin
Örnek: ../../communication/agent_send.sh PM "[{agent_id}] Görev tamamlandı"

Yoklama tipi ajanların bekleme durumuna (girdi bekleme) girmesi yasaktır.
Mutlaka beklemek istiyorsanız sleep 10 vb. çalıştırın → durmadan ilerleme veya başka iş arayın... tekrarlayın.
Aksi takdirde, bu STOP hooks tarafından yaklaşık 10K token yeniden girilir.

(Kalan STOP deneme sayısı: {threshold - stop_count} kez)
"""
    
    return reason


def main():
    """TODO: Add docstring"""
        # JSON dosyasını yükle
        input_data = json.load(sys.stdin)
        stop_hook_active = input_data.get('stop_hook_active', False)
        
        # Ajan bilgilerini alır
        agent_info = get_agent_info_from_cwd()
        if not agent_info:
            agent_info = {'agent_id': 'unknown'}
        
        # STOP sayısını artırır
        stop_count = increment_stop_count()
        
        # Blok nedenini oluşturur
        reason = generate_block_reason(stop_count, agent_info)
        
        # Çıkış kodu 2 ile stderr'ye çıktı (Stop olayını engelle)
        print(reason, file=sys.stderr)
        sys.exit(2)
        
    except Exception as e:
        # Hatalar sessizce işlenir
        sys.exit(0)


if __name__ == "__main__":
    main()
