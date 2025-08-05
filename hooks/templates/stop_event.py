#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# uvがある場合は以下で実行されます:
# #!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
VibeCodeHPC Stop Hook (イベントドリブン型エージェント用)
PG, IDは通常通り終了可能
"""

import json
import sys

def main():
    try:
        # JSONを読み込み（使わないが互換性のため）
        input_data = json.load(sys.stdin)
        
        # イベントドリブン型は通常終了
        sys.exit(0)
        
    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()