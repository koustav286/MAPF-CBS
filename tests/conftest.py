import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DATA = os.path.join(ROOT, "data")


def have_data() -> bool:
    return os.path.exists(os.path.join(DATA, "maps", "empty-32-32.map"))


needs_data = pytest.mark.skipif(not have_data(), reason="benchmarks not downloaded (scripts/download_benchmarks.py)")
