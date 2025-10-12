#!/usr/bin/env python3

"""
VibeCodeHPC bağlam (context) kullanım izleme sistemi
Claude Code JSONL günlüklerinden token kullanımını analiz eder ve çeşitli grafiklerle görselleştirir

Özellikler:
1. agent_and_pane_id_table.jsonl dosyasından oturum ID’lerini dinamik olarak alır
2. ~/.claude/projects/ altındaki JSONL günlüklerini izler
3. usage bilgilerini çıkarır ve toplam/akümülasyon token sayılarını hesaplar
4. Çeşitli grafik türleriyle görselleştirir (yığılmış çubuk, çizgi, genel görünüm)
5. auto-compact (~160K) için öngörü
6. Hafif önbellek sistemi (opsiyonel)
7. Hızlı durum (quick status) kontrolü
8. Zaman sınırı seçeneği (--max-minutes) ile grafik kapsamını kısıtlama
"""

import json
import os
import sys
import subprocess
import platform
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import matplotlib
matplotlib.use('Agg')  # GUI olmayan ortamlarda da çalışır
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict, OrderedDict
from typing import Dict, List, Tuple, Optional
import numpy as np
import pickle
import gzip

# # Grafik stil ayarları
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except:
    plt.style.use('seaborn-darkgrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

class ContextUsageMonitor:
    """Bağlam kullanım oranı izleme sınıfı"""

    # Claude Code'un bağlam sınırlaması
    
    # Claude Code bağlam sınırı
    CONTEXT_LIMIT = 200000  # 200K token (gösterim amaçlı)
    AUTO_COMPACT_THRESHOLD = 160000  # Gerçek auto-compact tetik noktası (tahmini)
    WARNING_THRESHOLD = 140000  # Uyarı eşiği
    
    def __init__(self, project_root: Path, use_cache: bool = True, max_minutes: Optional[int] = None):
        """Bağlam kullanım monitörünü başlat"""
        self.claude_projects_dir = self._get_claude_projects_dir()
        self.output_dir = project_root / "User-shared" / "visualizations"
        # # Önbellek ayarları
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_minutes = max_minutes  # Zaman sınırı (dakika)
        
        self.use_cache = use_cache
        self.cache_dir = project_root / ".cache" / "context_monitor"
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_claude_projects_dir(self) -> Path:
        """TODO: Add docstring"""
        return Path.home() / ".claude" / "projects"
    
    def get_cache_path(self, agent_id: str, jsonl_file: Path) -> Path:
        """TODO: Add docstring"""
        cache_name = f"{agent_id}_{jsonl_file.stem}.pkl.gz"
        return self.cache_dir / cache_name
    
        # # Dosyanın güncelleme zamanını karşılaştır
    def load_from_cache(self, cache_path: Path, jsonl_file: Path) -> Optional[List[Dict]]:
        """TODO: Add docstring"""
        if not self.use_cache or not cache_path.exists():
            return None  # JSONL daha yeni
            
        cache_mtime = cache_path.stat().st_mtime
        jsonl_mtime = jsonl_file.stat().st_mtime
        
        if jsonl_mtime > cache_mtime:
            return None  # JSONL daha yeni
            
        try:
            with gzip.open(cache_path, 'rb') as f:
                return pickle.load(f)
        except:
            return None
    
    def save_to_cache(self, cache_path: Path, data: List[Dict]):
        """TODO: Add docstring"""
        if not self.use_cache:
            return
            
        try:
            with gzip.open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except:
        # # Ajan bilgilerini yükle
            pass  # Önbelleğe alma başarısızsa yoksay
    
    def find_project_jsonl_files(self) -> Dict[str, List[Path]]:
        """TODO: Add docstring"""
        agent_table_path = self.project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
        
        if not agent_table_path.exists():
            print(f"⚠️  Aracı tablosu bulunamadı: {agent_table_path}")
            return {}
        
        agent_info = {}
        with open(agent_table_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    try:
                        data = json.loads(line)
                        if 'agent_id' in data and 'claude_session_id' in data:
                            agent_info[data['agent_id']] = {
        # # Platform tespiti ve yol dönüşümü
                                'session_id': data['claude_session_id'],
                                'working_dir': data.get('working_dir', ''),
        # # Her ajanın JSONL dosyasını ara
                                'cwd': data.get('cwd', '')  # Uyumluluk için cwd de kontrol edilir
                            }
                    except json.JSONDecodeError:
                        continue
        
            # # working_dir veya cwd'ye göre proje dizinini belirle
        if not agent_info:
            print("⚠️  agent_and_pane_id_table.jsonl içinde aracı oturumu bulunamadı")
                # # working_dir belirtilmişse
            return {}
        
                # # PM vb. durumlarda working_dir boşsa
        print(f"📊 Oturum ID’si olan {len(agent_info)} aracı bulundu")
        
            # # Yolu Claude projects dizin adı olarak dönüştür
            # # Claude Code dönüşüm kuralları (deneylerle belirlenmiştir):
            # # - Alfabe ve rakamlar (a-zA-Z0-9) dışındaki tüm karakterler '-' ile değiştirilir
            # # - Yol ayırıcı karakterler de '-' olarak dönüştürülür
            # # Örnek: /mnt/c/Users/test_v1.0.0 -> -mnt-c-Users-test-v1-0-0
        system = platform.system()
            # # Öncelikle yol ayırıcı karakterleri birleştir
        is_wsl = system == "Linux" and "microsoft" in platform.uname().release.lower()
                # Windows: Ters eğik çizgiyi eğik çizgiye dönüştür
        
        agent_files = {}
        for agent_id, info in agent_info.items():
            if not info['session_id']:
            # # Alfabe ve rakamlar dışındaki tüm karakterler (yol ayırıcı, özel karakterler, boşluk vb.) '-' ile değiştirilir
                continue
            
            # working_dir veya cwd’ye göre proje dizinini belirle
            working_dir = info['working_dir'] or info['cwd']
            
            if working_dir:
                # working_dir belirtilmişse
                full_path = self.project_root / working_dir
            else:
                full_path = self.project_root
            
            # Claude Code dönüştürme kuralları (deneysel olarak saptandı):
            # Örn: /mnt/c/Users/test_v1.0.0 -> -mnt-c-Users-test-v1-0-0
            import re
                # Proje dizini bulunamazsa, benzer isimler aranır
            
            if system == "Windows":
                # Windows: ters eğik çizgileri eğik çizgiye dönüştür
                path_str = str(full_path).replace('\\', '/')
            else:
                path_str = str(full_path)
            
            dir_name = re.sub(r'[^a-zA-Z0-9]', '-', path_str)
            
            project_dir = self.claude_projects_dir / dir_name
            if project_dir.exists():
                jsonl_file = project_dir / f"{info['session_id']}.jsonl"
        # # Önbellek kontrolü
                if jsonl_file.exists():
                    if agent_id not in agent_files:
                        agent_files[agent_id] = []
            # # Zaman sınırı ve last_n uygulanıyor
                    agent_files[agent_id].append(jsonl_file)
                    print(f"  ✅ {agent_id}: Found log ({jsonl_file.stat().st_size / 1024:.1f} KB)")
                else:
                    print(f"  ⚠️  {agent_id}: Session file not found: {jsonl_file.name}")
        # # Normal analiz işlemi
            else:
                similar_dirs = [d for d in self.claude_projects_dir.iterdir() 
                               if d.is_dir() and dir_name.lower() in d.name.lower()]
                if similar_dirs:
                    print(f"  ⚠️  {agent_id}: Directory not found. Similar: {[d.name for d in similar_dirs[:3]]}")
                else:
                        # # Sadece usage alanına sahip girdiler
                    print(f"  ⚠️  {agent_id}: Project dir not found: {dir_name}")
        
        return agent_files
    
    def parse_usage_data(self, jsonl_file: Path, agent_id: str, last_n: Optional[int] = None,
                        max_minutes: Optional[int] = None) -> List[Dict]:
        """JSONL dosyasından usage bilgilerini çıkar (önbellek ve zaman sınırı destekli)"""
        
        cache_path = self.get_cache_path(agent_id, jsonl_file)
        # # Önbelleğe kaydet
        cached_data = self.load_from_cache(cache_path, jsonl_file)
        # # Zaman sınırı ve last_n uygulanıyor
        if cached_data is not None:
            filtered_data = self._apply_time_filter(cached_data, max_minutes)
            if last_n and len(filtered_data) > last_n:
                return filtered_data[-last_n:]
            return filtered_data
        
        all_entries = []
        with open(jsonl_file, 'r') as f:
        # # İlk zaman damgasını al
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if 'message' in entry and isinstance(entry['message'], dict):
                            msg = entry['message']
                            if 'usage' in msg and isinstance(msg['usage'], dict) and 'timestamp' in entry:
                                all_entries.append({
                                    'timestamp': entry['timestamp'],
                                    'usage': msg['usage']
        # # Zaman sınırı ile filtreleme
                                })
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
        
        self.save_to_cache(cache_path, all_entries)
        
        filtered_entries = self._apply_time_filter(all_entries, max_minutes)
        if last_n and len(filtered_entries) > last_n:
            return filtered_entries[-last_n:]
        return filtered_entries
    
    def _apply_time_filter(self, entries: List[Dict], max_minutes: Optional[int]) -> List[Dict]:
        """TODO: Add docstring"""
        if not max_minutes or not entries:
            return entries
        
        first_timestamp = None
        for entry in entries:
            try:
            # # Zaman damgası dönüşümü
                ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                if first_timestamp is None or ts < first_timestamp:
                    first_timestamp = ts
                # # Kümülatif mod (geleneksel davranış)
            except:
                continue
        
        if not first_timestamp:
            return entries
        
        filtered = []
        for entry in entries:
            try:
                ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                elapsed_minutes = (ts - first_timestamp).total_seconds() / 60
                if elapsed_minutes <= max_minutes:
                # # Anlık görüntü modu (her anın context kullanımı)
                    filtered.append(entry)
            except:
                continue
        
        return filtered
    
    def calculate_cumulative_tokens(self, usage_entries: List[Dict], cumulative: bool = False) -> List[Tuple[datetime, Dict[str, int]]]:
        """TODO: Add docstring"""
        token_data = []
        total_input = 0
        total_cache_creation = 0
        total_cache_read = 0
        total_output = 0
        
        for entry in usage_entries:
            ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            
            usage = entry['usage']
            
            if cumulative:
            # # Varsayılan sayaç tabanlı (token sayısının belirtildiği loglar)
                total_input += usage.get('input_tokens', 0)
                total_cache_creation += usage.get('cache_creation_input_tokens', 0)
                total_cache_read += usage.get('cache_read_input_tokens', 0)
                total_output += usage.get('output_tokens', 0)
                
                token_data.append((ts, {
            # # Her ajan için ayrı grafik oluştur
                    'input': total_input,
                    'cache_creation': total_cache_creation,
                    'cache_read': total_cache_read,
                    'output': total_output,
                    'total': total_input + total_cache_creation + total_cache_read + total_output
                }))
            else:
                input_tokens = usage.get('input_tokens', 0)
                cache_creation = usage.get('cache_creation_input_tokens', 0)
        # # Uygun zamanlarda birden fazla grafik oluştur
                cache_read = usage.get('cache_read_input_tokens', 0)
        # # Belirtilen zaman sınırı veya kilometre taşında oluştur
                output = usage.get('output_tokens', 0)
            # Kilometre taşı zamanında, o zamana kadar grafik oluştur
                
                token_data.append((ts, {
                    'input': input_tokens,
            # # Kilometre taşı olmayan zaman belirtimi
                    'cache_creation': cache_creation,
                    'cache_read': cache_read,
            # # Zaman belirtilmemişse, genel ve kilometre taşı oluştur
            # # Genel grafik
                    'output': output,
            # # Proje başlangıcından geçen süreyi kontrol et
                    'total': input_tokens + cache_creation + cache_read + output
                }))
                # Şimdiye kadarki geçen süreyi hesapla
            
        return token_data
    
    def generate_all_graphs(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]],
                    # # Sadece geçen süreyi aşan kilometre taşlarını oluştur
                           graph_type: str = 'all', time_unit: str = 'minutes', cumulative: bool = False):
        """Belirtilen türde grafikleri üret"""
        self.is_cumulative = cumulative
        
        if graph_type in ['all', 'overview']:
            self.generate_overview_line_graph(all_agent_data, time_unit)
            
        if graph_type in ['all', 'stacked']:
        # # Başlıkta zaman sınırını göster
            self.generate_stacked_bar_chart(all_agent_data, x_axis='count')
        # # Proje başlangıç zamanını al
            self.generate_stacked_bar_chart(all_agent_data, x_axis='time')
            
        # # Sadece proje başlangıç zamanından sonraki verileri filtrele
        if graph_type in ['all', 'timeline']:
            self.generate_timeline_graph(all_agent_data)
            
                # # max_minutes belirtilmişse, sadece bu aralıktaki verileri kullan
        if graph_type in ['all', 'individual']:
            for agent_id, cumulative_data in all_agent_data.items():
                if cumulative_data:
                    self.generate_agent_detail_graphs(agent_id, cumulative_data)
    
    def generate_overview_line_graph(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]], 
                                    time_unit: str = 'minutes'):
        """Genel görünüm için hafif çizgi grafiği (basamak stili)
        
        Args:
        # # Her ajan için toplam token sayısının değişimi
            time_unit: 'seconds', 'minutes' veya 'hours' (varsayılan: 'minutes')
        """
        milestone_minutes = [30, 60, 90, 120, 180]
        
            # # Göreli zamana dönüştür (varsayılan dakika cinsindendir)
        if self.max_minutes and self.max_minutes in milestone_minutes:
            self._generate_single_overview_graph(all_agent_data, time_unit, self.max_minutes)
        elif self.max_minutes:
            # # Basamak stilinde (merdiven şeklinde) çizgi grafik
            self._generate_single_overview_graph(all_agent_data, time_unit, self.max_minutes)
        else:
        # # Eşik çizgisi
            self._generate_single_overview_graph(all_agent_data, time_unit, None)
            
            project_start = self._get_project_start_time(all_agent_data)
            if project_start:
        # # X ekseni etiketi (birime göre değişir)
                latest_time = max([t for data in all_agent_data.values() for t, _ in data]) if all_agent_data else None
                if latest_time:
        # # Y ekseni etiketi (kümülatif modda değişir)
                    elapsed_minutes = (latest_time - project_start).total_seconds() / 60
                    
                    for milestone in milestone_minutes:
                        if elapsed_minutes >= milestone:
                            self._generate_single_overview_graph(all_agent_data, time_unit, milestone)
    
    def _generate_single_overview_graph(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]], 
                                       time_unit: str, max_minutes: Optional[int]):
        """Tek bir genel görünüm grafiği üret"""
        # # X ekseni aralığını zaman sınırına göre ayarla
        plt.figure(figsize=(12, 8))
        
        title_suffix = f" (First {max_minutes} minutes)" if max_minutes else ""
        
        # # Dosya adına zaman sınırını dahil et
        project_start = self._get_project_start_time(all_agent_data)
            # Kilometre taşı zamanıysa özel dosya adı
        
        filtered_agent_data = {}
        if project_start:
            for agent_id, cumulative_data in all_agent_data.items():
                # max_minutes verilmişse o aralıktaki verileri kullan
                if max_minutes:
                    filtered_data = [(t, tokens) for t, tokens in cumulative_data 
                                   if t >= project_start and 
                                   (t - project_start).total_seconds() / 60 <= max_minutes]
                else:
                    filtered_data = [(t, tokens) for t, tokens in cumulative_data if t >= project_start]
                if filtered_data:
                    filtered_agent_data[agent_id] = filtered_data
        else:
            filtered_agent_data = all_agent_data
        
        for agent_id, cumulative_data in filtered_agent_data.items():
            if not cumulative_data:
                continue
                
            time_divisor = {'seconds': 1, 'minutes': 60, 'hours': 3600}[time_unit]
        # # Dosya yoksa tüm verilerin en eski zaman damgasını kullan
            times = [(t - project_start).total_seconds() / time_divisor for t, _ in cumulative_data]
            totals = [tokens['total'] for _, tokens in cumulative_data]
            
            plt.step(times, totals, where='post', marker='o', markersize=3, 
                    label=agent_id, alpha=0.8)
        
        plt.axhline(y=self.AUTO_COMPACT_THRESHOLD, color='red', 
                   linestyle='--', linewidth=2, label='Auto-compact (~160K)')
        plt.axhline(y=self.WARNING_THRESHOLD, color='orange', 
                   linestyle='--', linewidth=1, label='Warning (140K)')
        
        # # Renk haritası (statik → dinamik sırasıyla)
        unit_labels = {'seconds': 'Seconds', 'minutes': 'Minutes', 'hours': 'Hours'}
        plt.xlabel(f'{unit_labels[time_unit]} from Project Start')
        
        if hasattr(self, 'is_cumulative') and self.is_cumulative:
            plt.ylabel('Cumulative Token Usage')
            plt.title(f'Cumulative Token Usage Over Time{title_suffix}')
        else:
            plt.ylabel('Current Context Usage [tokens]')
            # # Günlük kayıt sayısına dayalı çubuk grafik
            plt.title(f'Context Usage Monitor{title_suffix}')
        plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
        plt.grid(True, alpha=0.3)
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K'))
        
                # # En son veri noktasını kullan
        if max_minutes:
                # # X ekseni konumu
            plt.xlim(0, max_minutes)
        
                # # Yığılmış çubuk grafik (statik olandan)
        plt.tight_layout()
        
        if max_minutes:
            if max_minutes in [30, 60, 90, 120, 180]:
                output_path = self.output_dir / f"context_usage_{max_minutes}min.png"
            else:
                output_path = self.output_dir / f"context_usage_overview_{max_minutes}min.png"
                # # Toplam değeri çubuğun üstünde göster
        else:
            output_path = self.output_dir / "context_usage_overview.png"
        
        plt.savefig(output_path, dpi=120, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Genel görünüm grafiği oluşturuldu: {output_path}")
    
    def _get_project_start_time(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]]) -> Optional[datetime]:
            # # Zaman tabanlı yığılmış alan grafiği
            # # En fazla token sayısına sahip ajanı seç
        """TODO: Add docstring"""
        start_time_file = self.project_root / "Agent-shared" / "project_start_time.txt"
        project_start = None
        
        if start_time_file.exists():
                # # Her token türünün değerini al
            try:
                # # Yığılmış alan grafiği
                with open(start_time_file, 'r') as f:
                    time_str = f.read().strip()
                    project_start = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except:
                pass
        
        if project_start is None:
            for agent_data in all_agent_data.values():
                if agent_data and (project_start is None or agent_data[0][0] < project_start):
                    project_start = agent_data[0][0]
        
        # # Ortak ayarlar
        return project_start
    
    def generate_stacked_bar_chart(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]],
                                  x_axis: str = 'count'):
        """Yığılmış çubuk grafik (daha statik olanlar altta)"""
        fig, ax = plt.subplots(figsize=(16, 10))
        
        token_types = ['cache_read', 'cache_creation', 'input', 'output']
        token_colors = {
            'cache_read': '#f39c12',     # turuncu (en statik)
            'cache_creation': '#2ecc71',  # yeşil
            'input': '#3498db',          # mavi
            'output': '#e74c3c'          # kırmızı (en dinamik)
        }
        
        if x_axis == 'count':
            bar_width = 0.8
            agent_positions = {}
            
            for idx, (agent_id, cumulative_data) in enumerate(all_agent_data.items()):
        # # Üst kısım: Tüm ajanların değişimi
                if not cumulative_data:
                    continue
                    
                latest_time, latest_tokens = cumulative_data[-1]
                
            # # Mevcut kullanım oranına göre renk değiştir
                x_pos = idx
                agent_positions[agent_id] = x_pos
                
                bottom = 0
                for token_type in token_types:
                    value = latest_tokens[token_type]
                    ax.bar(x_pos, value, bar_width, bottom=bottom,
                          color=token_colors[token_type], 
                          label=token_type if idx == 0 else "")
                    bottom += value
                
                total = latest_tokens['total']
                percentage = (total / self.AUTO_COMPACT_THRESHOLD) * 100
                ax.text(x_pos, total + 2000, f'{total:,}\n({percentage:.1f}%)', 
                       ha='center', va='bottom', fontsize=9)
            
            ax.set_xticks(list(agent_positions.values()))
            ax.set_xticklabels(list(agent_positions.keys()))
            ax.set_xlabel('Agents')
            
        else:  # x_axis == 'time'
        # # Alt kısım: Artış oranının görselleştirilmesi
            max_agent = max(all_agent_data.items(), 
                          key=lambda x: x[1][-1][1]['total'] if x[1] else 0)[0]
            
            if all_agent_data[max_agent]:
                data = all_agent_data[max_agent]
                times = [t for t, _ in data]
                
                token_values = {tt: [tokens[tt] for _, tokens in data] for tt in token_types}
                
        # # 1. Zaman serisi yığılmış alan grafiği
                bottom = np.zeros(len(times))
                for token_type in token_types:
                    values = np.array(token_values[token_type])
        # # Renk haritası (statik → dinamik sırasıyla)
                    ax.fill_between(times, bottom, bottom + values, 
                                   color=token_colors[token_type],
                                   label=token_type, alpha=0.8)
                    bottom += values
                
                ax.set_xlabel('Time')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        # # Üst kısım: Yığılmış alan grafiği
                plt.xticks(rotation=45)
                ax.set_title(f'Token Usage Timeline - {max_agent}')
        
        ax.axhline(y=self.AUTO_COMPACT_THRESHOLD, color='red', 
                  linestyle='--', linewidth=2, label='Auto-compact (~160K)')
        ax.axhline(y=self.WARNING_THRESHOLD, color='orange', 
                  linestyle='--', linewidth=1, label='Warning (140K)')
        
        ax.set_ylabel('Cumulative Tokens')
        # # En son istatistik bilgisi
        ax.set_title(f'VibeCodeHPC Token Usage (X-axis: {x_axis})')
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
        ax.grid(True, alpha=0.3, axis='y')
        # # Eşik çizgisi
        ax.set_ylim(0, self.CONTEXT_LIMIT * 1.05)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K'))
        
        plt.tight_layout()
        output_path = self.output_dir / f"context_usage_stacked_{x_axis}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Yığılmış grafik oluşturuldu ({x_axis} ekseni): {output_path}")
    
        # # Alt kısım: Her token türünün oran değişimi
    def generate_timeline_graph(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]]):
        """TODO: Add docstring"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [2, 1]})
        
        # # 2. Log sayısı tabanlı grafik
        for agent_id, cumulative_data in all_agent_data.items():
            if not cumulative_data:
                continue
                
            times = [t for t, _ in cumulative_data]
            totals = [tokens['total'] for _, tokens in cumulative_data]
            
        # # Her noktadaki oranı hesapla
            current_usage = totals[-1] if totals else 0
            if current_usage >= self.AUTO_COMPACT_THRESHOLD * 0.95:
                color = 'red'
                alpha = 1.0
            elif current_usage >= self.WARNING_THRESHOLD:
                color = 'orange'
                alpha = 0.8
            else:
                color = 'blue'
        # # Oran değişimini çiz
                alpha = 0.6
                
            ax1.step(times, totals, where='post', marker='o', markersize=3, 
                    label=f'{agent_id} ({current_usage/1000:.0f}K)', 
                    color=color, alpha=alpha)
        
        ax1.axhline(y=self.AUTO_COMPACT_THRESHOLD, color='red', 
                   linestyle='--', linewidth=2)
        ax1.set_ylabel('Total Tokens')
        ax1.set_title('Context Usage Timeline & Auto-compact Prediction')
        ax1.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K'))
        
        # # X ekseni: Log giriş numarası
        self._plot_growth_rates(ax2, all_agent_data)
        
        # # Renk kodlaması (kullanım oranına göre)
        plt.tight_layout()
        output_path = self.output_dir / "context_usage_timeline.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Zaman çizelgesi grafiği oluşturuldu: {output_path}")
    
    def generate_agent_detail_graphs(self, agent_id: str, cumulative_data: List[Tuple[datetime, Dict[str, int]]]):
        # # Dağılım grafiği ve çizgi
        """TODO: Add docstring"""
        
        # # Eşik çizgisi
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [2, 1]})
        
        times = [t for t, _ in cumulative_data]
        
        token_types = ['cache_read', 'cache_creation', 'input', 'output']
        token_colors = {
            'cache_read': '#f39c12',     # turuncu
            'cache_creation': '#2ecc71',  # yeşil
            'input': '#3498db',          # mavi
            'output': '#e74c3c'          # kırmızı
        }
        
        token_values = {tt: [tokens[tt] for _, tokens in cumulative_data] for tt in token_types}
        bottom = np.zeros(len(times))
        
        for token_type in token_types:
            values = np.array(token_values[token_type])
            ax1.fill_between(times, bottom, bottom + values, 
                           color=token_colors[token_type],
                           label=token_type, alpha=0.8)
            bottom += values
        
            # # Artış oranını hesapla (token/saat)
        latest_tokens = cumulative_data[-1][1]
        total = latest_tokens['total']
        percentage = (total / self.AUTO_COMPACT_THRESHOLD) * 100
        
        ax1.axhline(y=self.AUTO_COMPACT_THRESHOLD, color='red', 
                   linestyle='--', linewidth=2, label='Auto-compact')
        ax1.axhline(y=self.WARNING_THRESHOLD, color='orange', 
                   linestyle='--', linewidth=1, label='Warning')
        
        ax1.set_ylabel('Cumulative Tokens')
        ax1.set_title(f'{agent_id} - Token Usage Detail ({total:,} tokens, {percentage:.1f}%)')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K'))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        
        self._plot_token_ratios(ax2, cumulative_data, token_types)
        
        plt.tight_layout()
        output_path = self.output_dir / f"context_usage_{agent_id}_detail.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        self._generate_count_based_graph(agent_id, cumulative_data)
            # Başlık (kümülatif modda değişir)
        
        print(f"✅ {agent_id} için bireysel grafik oluşturma tamamlandı")
    
    def _plot_token_ratios(self, ax, cumulative_data: List[Tuple[datetime, Dict[str, int]]], 
                          token_types: List[str]):
        """Token türlerinin oran seyrini çiz"""
        times = [t for t, _ in cumulative_data]
        
        ratios = {tt: [] for tt in token_types}
        
            # # Ajan verilerini düzenle
        for _, tokens in cumulative_data:
            total = tokens['total']
            if total > 0:
                for tt in token_types:
                    ratios[tt].append(100 * tokens[tt] / total)
            else:
                for tt in token_types:
                # # otomatik sıkıştırmaya kadar tahmini süre
                    ratios[tt].append(0)
        
                    # # Son artış oranından tahmin
        for token_type in token_types:
            ax.plot(times, ratios[token_type], marker='o', markersize=3, 
                   label=f'{token_type} %', alpha=0.7)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Token Type Ratio (%)')
        ax.set_title('Token Type Distribution Over Time')
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
        ax.grid(True, alpha=0.3)
                # # Durum simgesi (kümülatif modda her zaman yeşil)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        ax.set_ylim(0, 100)
    
    def _generate_count_based_graph(self, agent_id: str, cumulative_data: List[Tuple[datetime, Dict[str, int]]]):
        """TODO: Add docstring"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        log_counts = list(range(1, len(cumulative_data) + 1))
        totals = [tokens['total'] for _, tokens in cumulative_data]
        
        colors = []
        for total in totals:
            if total >= self.AUTO_COMPACT_THRESHOLD * 0.95:
                colors.append('red')
            elif total >= self.WARNING_THRESHOLD:
                colors.append('orange')
            # # Token sayısına göre sırala
            else:
                colors.append('blue')
        
        ax.scatter(log_counts, totals, c=colors, s=50, alpha=0.7, edgecolors='black')
        ax.plot(log_counts, totals, 'b-', alpha=0.3)
        
        ax.axhline(y=self.AUTO_COMPACT_THRESHOLD, color='red', 
                  linestyle='--', linewidth=2, label='Auto-compact')
        ax.axhline(y=self.WARNING_THRESHOLD, color='orange', 
                  linestyle='--', linewidth=1, label='Warning')
        
        ax.set_xlabel('Log Entry Count')
        ax.set_ylabel('Total Tokens')
        ax.set_title(f'{agent_id} - Token Usage by Log Count')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K'))
        
        plt.tight_layout()
        output_path = self.output_dir / f"context_usage_{agent_id}_count.png"
        plt.savefig(output_path, dpi=120, bbox_inches='tight')
        plt.close()
    
    def _plot_growth_rates(self, ax, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]]):
        """TODO: Add docstring"""
        
        for agent_id, cumulative_data in all_agent_data.items():
            if len(cumulative_data) < 2:
                continue
                
            times = [t for t, _ in cumulative_data]
            totals = [tokens['total'] for _, tokens in cumulative_data]
            
            growth_rates = []
            growth_times = []
            
            for i in range(1, len(times)):
                time_diff = (times[i] - times[i-1]).total_seconds() / 3600  # Zaman birimi
                if time_diff > 0:
                    token_diff = totals[i] - totals[i-1]
                    rate = token_diff / time_diff
                    growth_rates.append(rate)
                    growth_times.append(times[i])
            
            if growth_rates:
                ax.plot(growth_times, growth_rates, marker='o', markersize=3, 
                       label=agent_id, alpha=0.7)
        
        # # Ajanları filtrele
        ax.set_xlabel('Time')
        ax.set_ylabel('Growth Rate (tokens/hour)')
        ax.set_title('Token Growth Rate Analysis')
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
        # # Tablo formatında çıktı
    def generate_summary_report(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]]):
        """TODO: Add docstring"""
        # # Verileri düzenle ve sırala
        report_path = self.output_dir / "context_usage_report.md"
        
        with open(report_path, 'w') as f:
            if hasattr(self, 'is_cumulative') and self.is_cumulative:
                f.write("# Kümülatif token kullanım raporu\n\n")
            else:
                f.write("# Bağlam kullanım durumu raporu\n\n")
            
            # # Durum değerlendirmesi
            f.write(f"Oluşturulma zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Özet\n\n")
            f.write("| Aracı | Toplam [token] | Kullanım oranı | Cache Read | Cache Create | Input | Output | Tahmini süre |\n")
            f.write("|-------|-----------------|----------------|------------|--------------|-------|--------|--------------|\n")
            
            # Ajan verilerini düzenle
            # # Tahmini süre
            agent_summaries = []
            
            for agent_id, cumulative_data in all_agent_data.items():
                if not cumulative_data:
                    continue
                    
                latest_time, latest_tokens = cumulative_data[-1]
                total = latest_tokens['total']
                percentage = (total / self.AUTO_COMPACT_THRESHOLD) * 100
                
                # auto-compact için tahmini süre
                est_hours = "N/A"
                if len(cumulative_data) >= 2:
                    # Son artış oranından tahmin edilir
                    recent_data = cumulative_data[-min(10, len(cumulative_data)):]
                    time_span = (recent_data[-1][0] - recent_data[0][0]).total_seconds() / 3600
                    token_increase = recent_data[-1][1]['total'] - recent_data[0][1]['total']
                    
                    if time_span > 0 and token_increase > 0:
                        rate = token_increase / time_span
                        remaining_tokens = self.AUTO_COMPACT_THRESHOLD - total
                        if remaining_tokens > 0:
        # # Token sayısına göre sırala
                            est_hours = f"{remaining_tokens / rate:.1f}h"
                
                # Durum simgesi (birikimli modda her zaman yeşil)
                if hasattr(self, 'is_cumulative') and self.is_cumulative:
                    status = "🟢"  # Kümülatif modda eşik değeri kontrolü yoktur
                else:
                    if total >= self.AUTO_COMPACT_THRESHOLD * 0.95:
                        status = "🔴"
                    elif total >= self.WARNING_THRESHOLD:
                        status = "🟡"
                    else:
                        status = "🟢"
                
                agent_summaries.append({
                    'agent_id': agent_id,
                    'status': status,
                    'total': total,
    # # Varsayılan
                    'percentage': percentage,
                    'tokens': latest_tokens,
                    'est_hours': est_hours
                })
            
            # Token sayısına göre sıralama
            agent_summaries.sort(key=lambda x: x['total'], reverse=True)
            
            for summary in agent_summaries:
                f.write(f"| {summary['status']} {summary['agent_id']} | "
                       f"{summary['total']:,} | "
                       f"{summary['percentage']:.1f}% | "
                       f"{summary['tokens']['cache_read']:,} | "
                       f"{summary['tokens']['cache_creation']:,} | "
                       f"{summary['tokens']['input']:,} | "
                       f"{summary['tokens']['output']:,} | "
                       f"{summary['est_hours']} |\n")
            
            f.write("\n## Görselleştirmeler\n\n")
            f.write("### Global Görünümler\n")
            f.write("- [Overview](context_usage_overview.png) - hafif çizgi grafik\n")
            f.write("- [Stacked by Count](context_usage_stacked_count.png) - aracı bazında yığın\n")
            f.write("- [Stacked by Time](context_usage_stacked_time.png) - zaman serisi yığın\n")
            f.write("- [Timeline](context_usage_timeline.png) - tahmin ve trend analizi\n\n")
            
            f.write("### Aracı Bazında Detaylar\n")
            for agent_id in sorted(all_agent_data.keys()):
    # # Proje kök dizinini al
                f.write(f"- {agent_id}: [Detay](context_usage_{agent_id}_detail.png) | "
                       f"[Adet](context_usage_{agent_id}_count.png)\n")
            
    # # Önbelleği temizle
            f.write("\n## Hızlı Erişim Komutları\n\n")
            f.write("```bash\n")
            f.write("# En güncel durum (metin çıktısı)\n")
            f.write("python telemetry/context_usage_monitor.py --status\n\n")
            f.write("# Belirli aracının durumunu görüntüle\n")
            f.write("python telemetry/context_usage_monitor.py --status --agent PG1.1.1\n\n")
            f.write("# Yalnızca özet grafiği üret (hafif)\n")
            f.write("python telemetry/context_usage_monitor.py --graph-type overview\n")
            f.write("```\n\n")
            
            f.write("## Cache Status\n\n")
            if self.use_cache and self.cache_dir.exists():
                cache_size = sum(f.stat().st_size for f in self.cache_dir.glob('*.pkl.gz'))
                f.write(f"- Cache directory: `.cache/context_monitor/`\n")
                f.write(f"- Total cache size: {cache_size / 1024 / 1024:.1f} MB\n")
        # # Her ajanın verilerini topla
                f.write(f"- Cache files: {len(list(self.cache_dir.glob('*.pkl.gz')))}\n")
            else:
                f.write("- Cache: Disabled\n")
        
            # # Birden fazla dosya varsa birleştir
        print(f"✅ Rapor oluşturma tamamlandı: {report_path}")
    
    def print_quick_status(self, all_agent_data: Dict[str, List[Tuple[datetime, Dict[str, int]]]], 
                          target_agent: Optional[str] = None):
        """Konsola mevcut durumu yazdır (hızlı erişim için)"""
                # Zaman serisine göre sırala
        
        print("\n" + "="*60)
        print(f"VibeCodeHPC Context Usage Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Ajanları filtreleme
        if target_agent:
                # # Hızlı durum gösterimi
            filtered_data = {k: v for k, v in all_agent_data.items() 
                           if target_agent.upper() in k.upper()}
                # # Grafik ve rapor oluşturma
        else:
            filtered_data = all_agent_data
        
        if not filtered_data:
            print(f"❌ Agent '{target_agent}' not found")
    # # Çalıştır
            return
        
        # Tablo formatında çıktı verme
        print(f"{'Agent':<10} {'Total':>10} {'%':>6} {'Status':<8} {'Est.Time':<10}")
        print("-"*50)
        
        # Verileri düzenle ve sırala
        agent_infos = []
        for agent_id, cumulative_data in filtered_data.items():
            if not cumulative_data:
    # # Gerekli paketlerin yüklü olup olmadığını kontrol et
                continue
                
            latest_time, latest_tokens = cumulative_data[-1]
            total = latest_tokens['total']
            percentage = (total / self.AUTO_COMPACT_THRESHOLD) * 100
            
            # Durum belirleme
            if total >= self.AUTO_COMPACT_THRESHOLD * 0.95:
                status = "🔴 CRITICAL"
            elif total >= self.WARNING_THRESHOLD:
                status = "🟡 WARNING"
            else:
                status = "🟢 OK"
            
            # Tahmini süre
            est_time = "N/A"
            if len(cumulative_data) >= 2:
                recent_data = cumulative_data[-min(10, len(cumulative_data)):]
                time_span = (recent_data[-1][0] - recent_data[0][0]).total_seconds() / 3600
                token_increase = recent_data[-1][1]['total'] - recent_data[0][1]['total']
                
                if time_span > 0 and token_increase > 0:
                    rate = token_increase / time_span
                    remaining_tokens = self.AUTO_COMPACT_THRESHOLD - total
                    if remaining_tokens > 0:
                        hours = remaining_tokens / rate
                        if hours < 1:
                            est_time = f"{int(hours*60)}min"
                        else:
                            est_time = f"{hours:.1f}h"
            
            agent_infos.append({
                'agent_id': agent_id,
                'total': total,
                'percentage': percentage,
                'status': status,
                'est_time': est_time
            })
        
        # Token sayısına göre sıralama
        agent_infos.sort(key=lambda x: x['total'], reverse=True)
        
        # Çıktı
        for info in agent_infos:
            print(f"{info['agent_id']:<10} {info['total']:>10,} {info['percentage']:>5.1f}% "
                  f"{info['status']:<8} {info['est_time']:<10}")
        
        print("\n" + "="*60)

def get_python_command():
    """Kullanılabilir Python komutlarını al"""
    commands = ['python3', 'python']
    
    for cmd in commands:
        try:
            result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return cmd
        except FileNotFoundError:
            continue
    
    # Varsayılan
    return 'python3'

def main():
    """Ana işlem"""
    parser = argparse.ArgumentParser(description='Monitor Claude Code context usage')
    parser.add_argument('--last-n', type=int, default=None,
                       help='Analyze only the last N log entries per agent')
    parser.add_argument('--graph-type', choices=['all', 'overview', 'stacked', 'timeline', 'individual'],
                       default='all', help='Type of graphs to generate')
    parser.add_argument('--time-unit', choices=['seconds', 'minutes', 'hours'],
                       default='minutes', help='Time unit for X-axis (default: minutes)')
    parser.add_argument('--cumulative', action='store_true',
                       help='Show cumulative token usage instead of per-request context size')
    parser.add_argument('--max-minutes', type=int, default=None,
                       help='Limit graph to first N minutes from project start (e.g., 60, 120, 180)')
    parser.add_argument('--no-cache', action='store_true',
                       help='Disable caching')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Clear cache before running')
    parser.add_argument('--watch', action='store_true', 
                       help='Continue monitoring (update every 5 minutes)')
    parser.add_argument('--interval', type=int, default=300,
                       help='Update interval in seconds (default: 300)')
    parser.add_argument('--status', action='store_true',
                       help='Show quick status in console (no graphs)')
    parser.add_argument('--agent', type=str, default=None,
                       help='Show status for specific agent only')
    
    args = parser.parse_args()
    
    # Proje kök dizinini alır
    project_root = Path(__file__).parent.parent
    monitor = ContextUsageMonitor(project_root, use_cache=not args.no_cache, max_minutes=args.max_minutes)
    
    # Önbellek temizleme
    if args.clear_cache and monitor.cache_dir.exists():
        import shutil
        shutil.rmtree(monitor.cache_dir)
        monitor.cache_dir.mkdir(parents=True, exist_ok=True)
        print("✅ Cache cleared")
    
    def update_once():
        """Sadece bir kez güncelle"""
        print("🔍 Scanning agent_and_pane_id_table.jsonl for session IDs...")
        jsonl_files = monitor.find_project_jsonl_files()
        
        if not jsonl_files:
            print("❌ No JSONL files found for agents")
            print(f"   Check: {monitor.project_root / 'Agent-shared' / 'agent_and_pane_id_table.jsonl'}")
            return
        
        print(f"📊 Found {len(jsonl_files)} agents with logs")
        
        # Her bir ajan için verileri toplar
        all_agent_data = {}
        for agent_id, files in jsonl_files.items():
            if not args.status:  # Durum gösterilirken ilerleme atlanır
                print(f"  - Processing {agent_id}...")
            
            # Birden fazla dosya varsa birleştirilecek
            all_usage_entries = []
            for jsonl_file in sorted(files):
                entries = monitor.parse_usage_data(jsonl_file, agent_id, args.last_n, args.max_minutes)
                all_usage_entries.extend(entries)
            
            if all_usage_entries:
                # Zaman serisine göre sıralama
                all_usage_entries.sort(key=lambda x: x['timestamp'])
                cumulative_data = monitor.calculate_cumulative_tokens(all_usage_entries, args.cumulative)
                all_agent_data[agent_id] = cumulative_data
        
        if all_agent_data:
            if args.status:
                # Hızlı Durum Görüntüleme
                monitor.print_quick_status(all_agent_data, args.agent)
            else:
                # Grafik ve rapor oluşturma
                monitor.generate_all_graphs(all_agent_data, args.graph_type, args.time_unit, args.cumulative)
                monitor.generate_summary_report(all_agent_data)
                print("✅ Context usage monitoring complete")
        else:
            print("❌ No usage data found in JSONL files")
    
    # Çalıştırma
    if args.watch:
        import time
        print(f"👁️  Watching mode enabled (interval: {args.interval}s)")
        while True:
            update_once()
            print(f"💤 Waiting {args.interval}s...")
            time.sleep(args.interval)
    else:
        update_once()

if __name__ == "__main__":
    try:
        import matplotlib
        import numpy
        main()
    except ImportError:
        print("❌ Error: Required packages not installed")
        print("Please install: pip3 install -r requirements.txt")
        sys.exit(1)
