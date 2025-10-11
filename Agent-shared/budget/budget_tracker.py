#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Durumsuz bütçe toplama sistemi
ChangeLog.md'den zaman bilgisi okunarak doğrudan hesaplanır
"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import sys


def find_project_root(start_path):
    """Proje kökünü bul (VibeCodeHPC yapısı)"""
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "Agent-shared").exists():
            return current
        current = current.parent
    
    return None


class BudgetTracker:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.rates = self.load_rates()
        
    def load_rates(self) -> Dict:
        """Kaynak gruplarına göre ücret oranı ayarı"""
        rates = {
            'cx-share': {'gpu': 1, 'rate': 0.007},
            'cx-interactive': {'gpu': 1, 'rate': 0.007},
            'cx-debug': {'gpu': 1, 'rate': 0.007},
            'cx-single': {'gpu': 4, 'rate': 0.007},
            'cx-small': {'gpu': 4, 'rate': 0.007},
            'cx-middle': {'gpu': 4, 'rate': 0.007},
            'cx-large': {'gpu': 4, 'rate': 0.007},
            'cx-middle2': {'gpu': 4, 'rate': 0.014},  # 2x oran
            'cxgfs-small': {'gpu': 4, 'rate': 0.007},
            'cxgfs-middle': {'gpu': 4, 'rate': 0.007},
        }
        
        # node_resource_groups.md'den ek bilgi yükleme (gelecekte)
        # config_path = self.project_root / "_remote_info/flow/node_resource_groups.md"
        
        return rates
    
    def extract_jobs(self) -> List[Dict]:
        """Tüm ChangeLog.md dosyalarından iş bilgilerini çıkar"""
        all_jobs = []
        
        for changelog in self.project_root.glob('**/ChangeLog.md'):
            # Agent-shared hariç tutulur
            if 'Agent-shared' in str(changelog) or '.git' in str(changelog):
                continue
                
            jobs = self.parse_changelog(changelog)
            all_jobs.extend(jobs)
            
        return all_jobs
    
    def parse_changelog(self, changelog_path: Path) -> List[Dict]:
        """ChangeLog.md içinden iş bilgilerini çıkar"""
        jobs = []
        
        try:
            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return jobs
        
        version_pattern = r'### v(\d+\.\d+\.\d+)(.*?)(?=###|\Z)'
        
        for match in re.finditer(version_pattern, content, re.DOTALL):
            version, section = match.groups()
            
            job_match = re.search(r'- \[.\] \*\*job\*\*(.*?)(?=- \[.\] \*\*|\Z)', section, re.DOTALL)
            if not job_match:
                continue
                
            job_section = job_match.group(1)
            
            job_info = {
                'version': version,
                'path': str(changelog_path),
                'job_id': self.extract_field(job_section, 'id'),
                'resource_group': self.extract_field(job_section, 'resource_group'),
                'start_time': self.extract_field(job_section, 'start_time'),
                'end_time': self.extract_field(job_section, 'end_time'),
                'cancelled_time': self.extract_field(job_section, 'cancelled_time'),
                'runtime_sec': self.extract_field(job_section, 'runtime_sec'),
                'status': self.extract_field(job_section, 'status'),
            }
            
            if job_info['job_id'] and job_info['resource_group']:
                # runtime_sec yoksa hesaplansın
                if not job_info['runtime_sec'] and job_info['start_time'] and job_info['end_time']:
                    try:
                        start = datetime.fromisoformat(job_info['start_time'].replace('Z', '+00:00'))
                        end = datetime.fromisoformat(job_info['end_time'].replace('Z', '+00:00'))
                        job_info['runtime_sec'] = str(int((end - start).total_seconds()))
                    except:
                        pass
                        
                jobs.append(job_info)
                
        return jobs
    
    def extract_field(self, text: str, field: str) -> str:
        """Alan değerini çıkar"""
        pattern = rf'- {field}:\s*`([^`]*)`'
        match = re.search(pattern, text)
        return match.group(1) if match else None
    
    def calculate_timeline(self, jobs: List[Dict], as_of: datetime = None) -> List[Tuple[datetime, float]]:
        """Olay tabanlı bütçe tüketimini hesapla
         
        Args:
            jobs: İş listesi
            as_of: Bu zamana kadar olan veriyi hesapla (None ise şu an)
        """
        events = []
        
        start_file = self.project_root / "Agent-shared/project_start_time.txt"
        if start_file.exists():
            try:
                project_start = datetime.fromisoformat(
                    start_file.read_text().strip().replace('Z', '+00:00')
                )
            except:
                project_start = datetime.now(timezone.utc) - timedelta(hours=1)
        else:
            project_start = datetime.now(timezone.utc) - timedelta(hours=1)
        
        for job in jobs:
            if not job.get('start_time'):
                continue
                
            end_time_str = job.get('end_time') or job.get('cancelled_time')
            if not end_time_str:
                if job.get('status') == 'running':
                    end_time_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                else:
                    continue
            
            try:
                start_time = datetime.fromisoformat(job['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except:
                continue
            
            resource_group = job.get('resource_group', 'cx-small')
            rate_info = self.rates.get(resource_group, {'gpu': 4, 'rate': 0.007})
            points_per_sec = rate_info['rate'] * rate_info['gpu']
            
            events.append({
                'time': start_time,
                'type': 'start',
                'rate': points_per_sec,
                'job': job
            })
            events.append({
                'time': end_time,
                'type': 'end',
                'rate': points_per_sec,
                'job': job
            })
        
        events.sort(key=lambda x: x['time'])
        
        timeline = [(project_start, 0.0)]
        current_rate = 0.0
        total_points = 0.0
        last_time = project_start
        
        for event in events:
            duration = (event['time'] - last_time).total_seconds()
            if duration > 0:
                total_points += current_rate * duration
            
            timeline.append((event['time'], total_points))
            
            if event['type'] == 'start':
                current_rate += event['rate']
            else:
                current_rate -= event['rate']
                
            last_time = event['time']
        
            
        return timeline
    
    def generate_report(self, as_of: datetime = None) -> Dict:
        """Rapor üretimi"""
        jobs = self.extract_jobs()
        timeline = self.calculate_timeline(jobs, as_of)
        
        current_total = timeline[-1][1] if timeline else 0
        
        snapshot_dir = self.project_root / 'Agent-shared/budget/snapshots'
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        cutoff_time = as_of if as_of else datetime.now(timezone.utc)
        timestamp = cutoff_time.strftime('%Y-%m-%dT%H-%M-%SZ')
        
        report = {
            'timestamp': timestamp,
            'total_points': current_total,
            'job_count': len([j for j in jobs if j.get('start_time')]),
            'running_jobs': len([j for j in jobs if j.get('status') == 'running']),
            'timeline_points': len(timeline),
        }
        
        report_full = {
            **report,
            'jobs': jobs,
            'timeline': [(t.isoformat(), p) for t, p in timeline]
        }

        # latest.jsonのみ上書き（タイムスタンプ付きファイルは生成しない）
        with open(snapshot_dir / 'latest.json', 'w') as f:
            json.dump(report_full, f, indent=2, default=str)
        
        return report
    
    def visualize_budget(self, output_path: Path = None, as_of: datetime = None):
        """Bütçe tüketim eğrisini görselleştir"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib import rcParams
            import numpy as np
            from scipy import stats
            
            try:
                rcParams['font.sans-serif'] = ['DejaVu Sans', 'Helvetica', 'Arial', 'sans-serif']
            except:
                pass
            
            jobs = self.extract_jobs()
            timeline = self.calculate_timeline(jobs, as_of)
            
            if not timeline:
                print("Grafiğe dönüştürülecek veri yok")
                return
            
            times = [t[0] for t in timeline]
            points = [t[1] for t in timeline]
            
            fig, ax = plt.subplots(figsize=(14, 7))
            
            ax.plot(times, points, linewidth=2, color='blue', label='Budget Usage', marker='o', markersize=4)
            ax.fill_between(times, points, alpha=0.3, color='blue')
            
            running_jobs = [j for j in jobs if j.get('status') == 'running']
            
            if len(times) >= 2:
                times_numeric = [(t - times[0]).total_seconds() for t in times]
                
                recent_start = max(0, int(len(times) * 0.7))
                recent_times = times_numeric[recent_start:]
                recent_points = points[recent_start:]
                
                if len(recent_times) >= 2:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(recent_times, recent_points)
                    
                    current_time = as_of or datetime.now(timezone.utc)
                    
                    if running_jobs:
                        last_time = times[-1]
                        
                        current_rate = 0
                        for job in running_jobs:
                            resource_group = job.get('resource_group', 'cx-small')
                            rate_info = self.rates.get(resource_group, {'gpu': 4, 'rate': 0.007})
                            current_rate += rate_info['rate'] * rate_info['gpu']
                        
                        duration = (current_time - last_time).total_seconds()
                        estimated_current = points[-1] + current_rate * duration
                        
                        future_time = last_time + timedelta(hours=1)
                        
                        pred_times = [last_time, future_time]
                        pred_times_numeric = [
                            (last_time - times[0]).total_seconds(),
                            (future_time - times[0]).total_seconds()
                        ]
                        pred_points = [slope * t + intercept for t in pred_times_numeric]
                    else:
                        # 実行中のジョブがない場合も線形回帰を使用
                        last_time = times[-1]
                        future_time = last_time + timedelta(hours=1)
                        
                        pred_times = [last_time, future_time]
                        pred_times_numeric = [
                            (last_time - times[0]).total_seconds(),
                            (future_time - times[0]).total_seconds()
                        ]
                        pred_points = [slope * t + intercept for t in pred_times_numeric]
                        
                        estimated_current = points[-1]
                    
                    ax.plot(pred_times, pred_points, '--', linewidth=2, color='purple', 
                           label=f'Prediction (rate: {slope*3600:.1f} pt/hr)', alpha=0.7)
                    
                    budget_limits = {
                        'Minimum (100pt)': 100,
                        'Expected (500pt)': 500,
                        'Deadline (1000pt)': 1000
                    }
                    
                    if running_jobs:
                        current_points = estimated_current
                    else:
                        current_points = points[-1]
                    
                    predictions_text = []
                    for label, limit in budget_limits.items():
                        if current_points < limit and slope > 0:
                            seconds_to_limit = (limit - intercept) / slope
                            eta = times[0] + timedelta(seconds=seconds_to_limit)
                            hours_from_last = (eta - times[-1]).total_seconds() / 3600
                            if hours_from_last > 0:
                                predictions_text.append(f"{label}: {eta.strftime('%m-%d %H:%M')} (+{hours_from_last:.1f}h from last data)")
                    
                    if predictions_text:
                        prediction_str = "ETA:\n" + "\n".join(predictions_text)
                        ax.text(0.98, 0.98, prediction_str, transform=ax.transAxes,
                               verticalalignment='top', horizontalalignment='right', fontsize=10,
                               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
            
            budget_limits = {
                'Minimum (100pt)': 100,
                'Expected (500pt)': 500,
                'Deadline (1000pt)': 1000
            }
            
            colors = ['green', 'orange', 'red']
            for (label, limit), color in zip(budget_limits.items(), colors):
                ax.axhline(y=limit, color=color, linestyle='--', alpha=0.7, label=label)
            
            running_jobs = [j for j in jobs if j.get('status') == 'running']
            if running_jobs:
                ax.annotate('Running jobs\n(estimated)', 
                           xy=(times[-1], points[-1]),
                           xytext=(10, 10), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
            
            ax.set_xlabel('Time (UTC)')
            ax.set_ylabel('Points')
            ax.set_title('YBH Budget Usage Timeline')
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig.autofmt_xdate()  # Tarih etiketlerini eğimli yap
            
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')
            
            ax.set_ylim(bottom=0)
            
            if output_path is None:
                output_path = self.project_root / "User-shared" / "visualizations" / "budget_usage.png"
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            print(f"Grafik kaydedildi: {output_path}")
            
            # 実行中ジョブの警告
            if running_jobs:
                print(f"Not: {len(running_jobs)} adet çalışan iş içerdiği için grafiğin sağ uç değerleri tahminidir")
            
        except ImportError:
            print("ERROR: matplotlib kurulu değil")
            print("Lütfen: pip install matplotlib komutunu çalıştırın")
        except Exception as e:
            print(f"Grafik oluşturma hatası: {e}")
    
    def print_summary(self, as_of: datetime = None):
        """簡易サマリー表示"""
        jobs = self.extract_jobs()
        timeline = self.calculate_timeline(jobs, as_of)
        
        total = timeline[-1][1] if timeline else 0
        running = len([j for j in jobs if j.get('status') == 'running'])
        completed = len([j for j in jobs if j.get('status') == 'completed'])
        
        print(f"=== Bütçe Toplama Özeti ===")
        print(f"Toplam tüketim: {total:.1f} puan")
        print(f"İş sayısı: tamamlanan={completed}, çalışan={running}")
        
        # 予算に対する割合（仮定値）
        budget_limits = {'Minimum': 100, 'Beklenen': 500, 'Üst sınır': 1000}
        for label, limit in budget_limits.items():
            percentage = (total / limit * 100) if limit > 0 else 0
            print(f"{label}: {percentage:.1f}%")
        
        if running > 0:
            print(f"Not: {running} adet çalışan iş için değerler mevcut zamana kadar tahmindir")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Bütçe toplama sistemi')
    parser.add_argument('--summary', action='store_true', help='Basit özet göster')
    parser.add_argument('--report', action='store_true', help='Ayrıntılı rapor oluştur')
    parser.add_argument('--json', action='store_true', help='JSON formatında çıktı ver')
    parser.add_argument('--graph', action='store_true', help='Bütçe tüketim grafiği oluştur (önerilmez: varsayılan olarak oluşturulur)')
    parser.add_argument('--output', type=str, help='Grafik çıktı yolu')
    parser.add_argument('--as-of', type=str, help='Belirtilen zamana kadar olan verileri göster (YYYY-MM-DDTHH:MM:SSZ)')
    
    args = parser.parse_args()
    
    # プロジェクトルートを探す
    project_root = find_project_root(Path.cwd())
    if not project_root:
        print("ERROR: Proje kökü bulunamadı", file=sys.stderr)
        sys.exit(1)
    
    tracker = BudgetTracker(project_root)
    
    # --as-of パラメータの解析
    as_of = None
    if args.as_of:
        try:
            # ISO 8601形式でパース (Z を UTC として解釈)
            as_of_str = args.as_of.replace('Z', '+00:00')
            as_of = datetime.fromisoformat(as_of_str)
            if as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=timezone.utc)
            print(f"Zaman belirtildi: {as_of.strftime('%Y-%m-%d %H:%M:%S UTC')} tarihine kadar olan veriler gösterilecek")
        except ValueError as e:
            print(f"ERROR: --as-of biçimi geçersiz: {e}")
            print("Doğru biçim: YYYY-MM-DDTHH:MM:SSZ (ör.: 2025-08-20T01:00:00Z)")
            sys.exit(1)
    
    if args.summary:
        tracker.print_summary(as_of)
    elif args.json:
        report = tracker.generate_report(as_of)
        print(json.dumps(report, indent=2))
    elif args.graph:
        output_path = Path(args.output) if args.output else None
        tracker.visualize_budget(output_path, as_of)
    else:
        # デフォルト動作：レポート生成とグラフ保存
        report = tracker.generate_report(as_of)
        print(f"Rapor oluşturuldu: {report['total_points']:.1f} puan tüketildi")
        print(f"Ayrıntılar: Agent-shared/budget/snapshots/latest.json")
        
        # グラフも自動生成（画像を読み込まずに保存のみ）
        tracker.visualize_budget(as_of=as_of)


if __name__ == "__main__":
    main()
