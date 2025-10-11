#!/usr/bin/env python3
"""
ChangeLog.md dosyasına yeni giriş eklemeyi kolaylaştıran yardımcı betik.
PG ajanı kod üretimi sırasında kullanır.
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path


def get_current_utc():
    """Geçerli UTC zamanı al (saniye çözünürlüğünde)"""
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def create_changelog_entry(version, changes, result="Yürütülmedi", comment=""):
    """ChangeLog girdisi için şablon üret"""
    
    template = f"""### v{version}
**Değişiklikler**: "{changes}"  
**Sonuç**: {result}  
**Yorum**: "{comment}"  

<details>

- **Oluşturulma zamanı**: `{get_current_utc()}`
- [ ] **compile**
    - status: `pending`
- [ ] **job**
    - id: `pending`
    - status: `pending`
- [ ] **test**
    - status: `pending`
    - performance: `pending`
    - unit: `GFLOPS`

</details>
"""
    return template


def append_to_changelog(changelog_path, entry):
    """ChangeLog.md dosyasına giriş ekle (en yeni giriş üstte)"""
    
    if not changelog_path.exists():
        header = f"""# ChangeLog.md
Oluşturma başlangıcı: {get_current_utc()}

## Change Log

"""
        changelog_path.write_text(header + entry, encoding='utf-8')
    else:
        content = changelog_path.read_text(encoding='utf-8')
        
        # "## Change Log" başlığından sonra ekle
        marker = "## Change Log"
        if marker in content:
            parts = content.split(marker, 1)
            new_content = parts[0] + marker + "\n\n" + entry + "\n" + parts[1].lstrip()
            changelog_path.write_text(new_content, encoding='utf-8')
        else:
            changelog_path.write_text(content + "\n" + entry, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='ChangeLog.md girdisi oluşturma yardımcı aracı')
    parser.add_argument('--version', '-v', required=True, help='Sürüm numarası (örn: 1.0.0)')
    parser.add_argument('--changes', '-c', required=True, help='Değişikliklerin açıklaması')
    parser.add_argument('--result', '-r', default='Yürütülmedi', help='Sonuç (varsayılan: Yürütülmedi)')
    parser.add_argument('--comment', '-m', default='', help='Yorum')
    parser.add_argument('--file', '-f', default='ChangeLog.md', help='ChangeLog dosya yolu')
    parser.add_argument('--dry-run', action='store_true', help='Dosyayı değiştirmeden yalnızca çıktıyı göster')
    
    args = parser.parse_args()
    
    entry = create_changelog_entry(args.version, args.changes, args.result, args.comment)
    
    if args.dry_run:
        print("=== Oluşturulacak giriş ===")
        print(entry)
    else:
        changelog_path = Path(args.file)
        append_to_changelog(changelog_path, entry)
        print(f"✅ ChangeLog.md dosyasına v{args.version} eklendi")
        print(f"   Oluşturulma zamanı: {get_current_utc()}")


if __name__ == "__main__":
    main()
