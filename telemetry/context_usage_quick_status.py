#!/usr/bin/env python3
"""
VibeCodeHPC Bağlam Kullanımı Hızlı Durum
Gerçek zamanlı token kullanımını hızlıca kontrol etme aracı

İleride OpenTelemetry metrikleri olarak gönderim planlanmaktadır
"""

import json
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, List, Tuple, Optional

class ContextQuickStatus:
    """Bağlam kullanım oranını hızlıca doğrulama sınıfı"""
    
    # Claude Code'un bağlam sınırlaması
    AUTO_COMPACT_THRESHOLD = 160000  # Gerçek auto-compact oluşum noktası (tahmini)
    WARNING_THRESHOLD = 140000  # Uyarı eşik değeri
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.claude_projects_dir = Path.home() / ".claude" / "projects"
    
    def get_latest_usage(self, agent_id: Optional[str] = None) -> Dict[str, Dict]:
        """En güncel token kullanım durumunu al (hızlı sürüm)"""
        
        # Proje dizini adını oluşturur
        # Claude Code dönüşüm kuralı: İngilizce harf ve rakamlar dışındaki tüm karakterler '-' ile değiştirilir
        import re
        project_dir_name = re.sub(r'[^a-zA-Z0-9]', '-', str(self.project_root))
        if project_dir_name.startswith('-'):
            project_dir_name = project_dir_name[1:]
            
        project_claude_dir = self.claude_projects_dir / project_dir_name
        
        if not project_claude_dir.exists():
            return {}
            
        # session_id ile ajan arasındaki eşleşmeyi alır
        agent_sessions = self._get_agent_sessions()
        
        # Her JSONL dosyasının yalnızca en son girişini alır
        agent_status = {}
        
        for jsonl_file in project_claude_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            current_agent_id = agent_sessions.get(session_id, f"Unknown_{session_id[:8]}")
            
            # Belirli bir ajan belirtilmişse filtre uygula
            if agent_id and agent_id.upper() not in current_agent_id.upper():
                continue
            
            # Dosyanın sonundan geriye doğru okuyarak en son usage değerini bulur
            latest_usage = self._get_latest_usage_from_file(jsonl_file)
            
            if latest_usage:
                agent_status[current_agent_id] = latest_usage
        
        return agent_status
    
    def _get_agent_sessions(self) -> Dict[str, str]:
        """agent_and_pane_id_table.jsonl içinden session_id ile agent_id eşlemesini al"""
        sessions = {}
        
        agent_table_path = self.project_root / "Agent-shared" / "agent_and_pane_id_table.jsonl"
        if agent_table_path.exists():
            with open(agent_table_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        try:
                            data = json.loads(line)
                            session_id = data.get('claude_session_id')
                            agent_id = data.get('agent_id')
                            if session_id and agent_id:
                                sessions[session_id] = agent_id
                        except json.JSONDecodeError:
                            continue
                            
        return sessions
    
    def _get_latest_usage_from_file(self, jsonl_file: Path) -> Optional[Dict]:
        """JSONL dosyasından en güncel kullanım bilgisini al (sondan tarama)"""
        
        # Dosyayı ters sırayla okuma (verimli)
        with open(jsonl_file, 'rb') as f:
            # Dosyanın sonundan okuma
            f.seek(0, 2)  # Dosya sonuna kadar
            file_size = f.tell()
            
            # Maksimum 10MB kadar geriye doğru arama yapar
            search_size = min(file_size, 10 * 1024 * 1024)
            f.seek(max(0, file_size - search_size))
            
            # Kalanı oku
            content = f.read().decode('utf-8', errors='ignore')
            lines = content.strip().split('\n')
            
            # Ters sırayla işleme
            for line in reversed(lines):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if 'message' in entry and isinstance(entry['message'], dict):
                            msg = entry['message']
                            if 'usage' in msg and isinstance(msg['usage'], dict):
                                # Kümülatif hesaplama
                                usage = msg['usage']
                                total = (usage.get('input_tokens', 0) + 
                                       usage.get('cache_creation_input_tokens', 0) +
                                       usage.get('cache_read_input_tokens', 0) +
                                       usage.get('output_tokens', 0))
                                
                                return {
                                    'timestamp': entry.get('timestamp', 'N/A'),
                                    'total': total,
                                    'input': usage.get('input_tokens', 0),
                                    'cache_creation': usage.get('cache_creation_input_tokens', 0),
                                    'cache_read': usage.get('cache_read_input_tokens', 0),
                                    'output': usage.get('output_tokens', 0)
                                }
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
        
        return None
    
    def print_status(self, agent_status: Dict[str, Dict]):
        """Durumu görüntüle"""
        
        if not agent_status:
            print("❌ No usage data found")
            return
        
        print("\n" + "="*70)
        print(f"VibeCodeHPC Context Usage - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        print(f"{'Agent':<10} {'Total':>10} {'%':>6} {'Status':<10} {'Last Update'}")
        print("-"*70)
        
        # Sıralama için veri hazırlığı
        sorted_agents = []
        for agent_id, usage in agent_status.items():
            total = usage['total']
            percentage = (total / self.AUTO_COMPACT_THRESHOLD) * 100
            
            # Durum değerlendirmesi
            if total >= self.AUTO_COMPACT_THRESHOLD * 0.95:
                status = "🔴 CRITICAL"
            elif total >= self.WARNING_THRESHOLD:
                status = "🟡 WARNING"
            else:
                status = "🟢 OK"
            
            # Zaman damgası işlemi
            timestamp = usage.get('timestamp', 'N/A')
            if timestamp != 'N/A':
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_ago = datetime.now(dt.tzinfo) - dt
                    if time_ago.total_seconds() < 60:
                        time_str = "just now"
                    elif time_ago.total_seconds() < 3600:
                        time_str = f"{int(time_ago.total_seconds() / 60)}m ago"
                    else:
                        time_str = f"{int(time_ago.total_seconds() / 3600)}h ago"
                except:
                    time_str = timestamp
            else:
                time_str = 'N/A'
            
            sorted_agents.append({
                'agent_id': agent_id,
                'total': total,
                'percentage': percentage,
                'status': status,
                'time_str': time_str
            })
        
        # Token sayısına göre sıralama
        sorted_agents.sort(key=lambda x: x['total'], reverse=True)
        
        # Çıktı
        for agent in sorted_agents:
            print(f"{agent['agent_id']:<10} {agent['total']:>10,} {agent['percentage']:>5.1f}% "
                  f"{agent['status']:<10} {agent['time_str']}")
        
        print("\n" + "="*70)
    
    def export_to_otel_format(self, agent_status: Dict[str, Dict]) -> List[Dict]:
        """OpenTelemetry biçimine dönüştür (gelecek kullanım için)"""
        metrics = []
        
        for agent_id, usage in agent_status.items():
            metric = {
                'name': 'claude_code_context_usage',
                'unit': 'tokens',
                'value': usage['total'],
                'attributes': {
                    'agent_id': agent_id,
                    'project': str(self.project_root.name),
                    'input_tokens': usage['input'],
                    'cache_creation_tokens': usage['cache_creation'],
                    'cache_read_tokens': usage['cache_read'],
                    'output_tokens': usage['output']
                },
                'timestamp': usage.get('timestamp', datetime.now().isoformat())
            }
            metrics.append(metric)
        
        return metrics

def main():
    """Ana işlem"""
    parser = argparse.ArgumentParser(description='Quick context usage status check')
    parser.add_argument('--agent', type=str, default=None,
                       help='Show status for specific agent only')
    parser.add_argument('--json', action='store_true',
                       help='Output in JSON format')
    parser.add_argument('--otel', action='store_true',
                       help='Output in OpenTelemetry format (future use)')
    
    args = parser.parse_args()
    
    # Proje kök dizinini alır
    project_root = Path.cwd()
    status_checker = ContextQuickStatus(project_root)
    
    # En güncel durumu alır
    agent_status = status_checker.get_latest_usage(args.agent)
    
    if args.json:
        # JSON formatında çıktı verir
        print(json.dumps(agent_status, indent=2))
    elif args.otel:
        # OpenTelemetry formatında çıktı (gelecekteki uygulama)
        metrics = status_checker.export_to_otel_format(agent_status)
        print(json.dumps(metrics, indent=2))
    else:
        # Normal görüntüleme
        status_checker.print_status(agent_status)

if __name__ == "__main__":
    main()
