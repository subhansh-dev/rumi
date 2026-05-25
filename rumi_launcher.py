#!/usr/bin/env python3
"""RUMI — console entry point.

Run `rumi` from anywhere after installing:
    pip install -e .
    rumi
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from main import main

if __name__ == "__main__":
    main()
