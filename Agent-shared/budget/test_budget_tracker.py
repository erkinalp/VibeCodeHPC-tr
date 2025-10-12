#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
budget_tracker.py için test hata ayıklama kodu
Dummy ChangeLog.md oluşturarak bütçe toplama işlemini doğrulama
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

# Proje kök dizinini bul ve budget_tracker'ı içe aktar
def find_project_root(start_path):
    """Proje kökünü (VibeCodeHPC-jp) bul"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None

project_root = find_project_root(Path.cwd())
if not project_root:
    print("ERROR: Proje kökü bulunamadı")
    sys.exit(1)

# budget_tracker'ı içe aktarın
sys.path.insert(0, str(project_root / "Agent-shared" / "budget"))
from budget_tracker import BudgetTracker

def create_test_changelog(temp_dir, pg_name, jobs):
    """Test için ChangeLog.md oluştur"""
    changelog_path = temp_dir / pg_name / "ChangeLog.md"
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = "# ChangeLog\n\n"
    
    for job in jobs:
        version = job.get('version', '1.0.0')
        content += f"### v{version}\n"
        content += f"**Oluşturma zamanı**: `{job.get('generation_time', datetime.utcnow().isoformat())}Z`\n"
        content += f"**Değişiklikler**: \"{job.get('change', 'Test değişikliği')}\"\n"
        content += f"**Sonuç**: {job.get('result', '100 GFLOPS')}\n\n"
        content += "<details>\n\n"
        content += f"- [x] **job**\n"
        content += f"    - id: `{job.get('job_id', '12345')}`\n"
        content += f"    - resource_group: `{job.get('resource_group', 'cx-small')}`\n"
        
        if job.get('start_time'):
            content += f"    - start_time: `{job['start_time']}`\n"
        
        if job.get('end_time'):
            content += f"    - end_time: `{job['end_time']}`\n"
        elif job.get('cancelled_time'):
            content += f"    - cancelled_time: `{job['cancelled_time']}`\n"
            
        if job.get('runtime_sec'):
            content += f"    - runtime_sec: `{job['runtime_sec']}`\n"
            
        content += f"    - status: `{job.get('status', 'completed')}`\n"
        content += "\n</details>\n\n"
    
    changelog_path.write_text(content, encoding='utf-8')
    return changelog_path

def run_test():
    """Test çalıştırma"""
    print("=" * 60)
    print("budget_tracker.py test başlangıcı")
    print("=" * 60)
    
# Geçici dizin oluşturma
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
# Proje yapısını taklit etme
        (temp_path / "Agent-shared").mkdir()
        (temp_path / "CLAUDE.md").touch()
        
# Proje başlangıç zamanı
        start_time = datetime.utcnow() - timedelta(hours=2)
        (temp_path / "Agent-shared" / "project_start_time.txt").write_text(
            start_time.isoformat() + "Z"
        )
        
# Test senaryosu 1: Tek iş
        print("\n[Test1] Tek iş hesaplama")
        print("-" * 40)
        
        job1_start = start_time + timedelta(minutes=10)
        job1_end = job1_start + timedelta(minutes=30)
        
        create_test_changelog(temp_path / "Flow/TypeII/single-node/gcc/OpenMP", "PG1.1.1", [{
            'version': '1.0.0',
            'job_id': 'job_001',
            'resource_group': 'cx-small',
            'start_time': job1_start.isoformat() + 'Z',
            'end_time': job1_end.isoformat() + 'Z',
            'runtime_sec': '1800',
            'status': 'completed'
        }])
        
        tracker = BudgetTracker(temp_path)
        jobs = tracker.extract_jobs()
        print(f"İş sayısı: {len(jobs)}")
        
        timeline = tracker.calculate_timeline(jobs)
        if timeline:
            total_points = timeline[-1][1]
            print(f"Toplam tüketilen puan: {total_points:.2f}")
            print(f"Beklenen değer: {0.028 * 1800:.2f} (cx-small: 4GPU x 0.007/sec x 1800sec)")
        
        # Test Senaryosu 2: Paralel İş
        print("\n[Test2] Paralel iş hesaplama")
        print("-" * 40)
        
        # PG1.1.1 iş (mevcut)
        # PG1.1.2 iş (kısmen örtüşen)
        job2_start = job1_start + timedelta(minutes=15)  # job1'in ortasında başlatıldı
        job2_end = job1_end + timedelta(minutes=10)     # job1'in ardından sonlandırılır
        
        create_test_changelog(temp_path / "Flow/TypeII/single-node/gcc/MPI", "PG1.1.2", [{
            'version': '1.0.0', 
            'job_id': 'job_002',
            'resource_group': 'cx-middle',  # farklı kaynak grubu
            'start_time': job2_start.isoformat() + 'Z',
            'end_time': job2_end.isoformat() + 'Z',
            'runtime_sec': '1500',
            'status': 'completed'
        }])
        
        tracker = BudgetTracker(temp_path)
        jobs = tracker.extract_jobs()
        print(f"İş sayısı: {len(jobs)}")
        
        timeline = tracker.calculate_timeline(jobs)
        if timeline:
            total_points = timeline[-1][1]
            print(f"Toplam tüketilen puan: {total_points:.2f}")
            
            # Beklenen değer       # Beklenen değer hesaplama (manuel)
            # job1: 0.028 * 1800 = 50.4
            # job2: 0.028 * 1500 = 42.0  (cx-middle de 4GPU x 0.007)
            # Toplam: 92.4
            print(f"Beklenen değer: 92.4 (job1: 50.4 + job2: 42.0)")
        
# Test senaryosu 3: Çalışan iş
        print("\n[Test3] Çalışan iş hesaplama")
        print("-" * 40)
        
        job3_start = datetime.utcnow() - timedelta(minutes=5)
        
        create_test_changelog(temp_path / "Flow/TypeII/single-node/intel/OpenMP", "PG1.2.1", [{
            'version': '2.0.0',
            'job_id': 'job_003',
            'resource_group': 'cx-share',  # 1 GPU
            'start_time': job3_start.isoformat() + 'Z',
# end_time yok - Çalışıyor
            'status': 'running'
        }])
        
        tracker = BudgetTracker(temp_path)
        jobs = tracker.extract_jobs()
        print(f"İş sayısı: {len(jobs)}")
        
        running_jobs = [j for j in jobs if j.get('status') == 'running']
        print(f"Çalışan iş sayısı: {len(running_jobs)}")
        
        timeline = tracker.calculate_timeline(jobs)
        if timeline:
            total_points = timeline[-1][1]
            print(f"Toplam tüketilen puan (çalışan dahil): {total_points:.2f}")
            print("Not: Çalışan işler mevcut zamana kadar hesaplanır")
        
        # Test Senaryosu 4: Rapor Oluşturma
        print("\n[Test4] Rapor oluşturma")
        print("-" * 40)
        
        # snapshots dizini oluştur
        snapshot_dir = temp_path / "Agent-shared" / "budget" / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        report = tracker.generate_report()
        print(f"Rapor oluşturma tamamlandı:")
        print(f"  - Zaman damgası: {report['timestamp']}")
        print(f"  - Toplam puan: {report['total_points']:.2f}")
        print(f"  - İş sayısı: {report['job_count']}")
        print(f"  - Çalışan: {report['running_jobs']}")
        print(f"  - Zaman çizgisi noktaları: {report['timeline_points']}")
        
        # Dosya kontrolü
        latest_file = snapshot_dir / "latest.json"
        if latest_file.exists():
            print(f"  - latest.json oluşturma: ✅")
        else:
            print(f"  - latest.json oluşturma: ❌")
        
        # Test senaryosu 5: Özet görüntüleme
        print("\n[Test5] Özet görüntüleme")
        print("-" * 40)
        tracker.print_summary()
        
        # Test senaryosu 6: Grafik oluşturma
        print("\n[Test6] Grafik oluşturma")
        print("-" * 40)
        
        graph_path = temp_path / "test_budget_graph.png"
        tracker.visualize_budget(graph_path)
        
        if graph_path.exists():
            print(f"  - Grafik dosya boyutu: {graph_path.stat().st_size} bytes")
        else:
            print(f"  - Grafik oluşturma başarısız")

if __name__ == "__main__":
    try:
        run_test()
        print("\n" + "=" * 60)
        print("✅ Test tamamlandı")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
