#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCodeHPC Stop Hook (olay güdümlü ajanlar için)
PG ve ID normal şekilde sonlandırılabilir
"""

import json
import sys

def main():
    try:
        input_data = json.load(sys.stdin)
        
        sys.exit(0)
        
    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()
