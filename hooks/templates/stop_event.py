#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook (イベントドリブン型Ajan用)
PG, IDは通常通り終了可能
"""

import json
import sys

def main():
    try:
        # JSONをOkuma（使わないが互換性のため）
        input_data = json.load(sys.stdin)
        
        # イベントドリブン型は通常終了
        sys.exit(0)
        
    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()