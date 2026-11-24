"""Shared helpers for the experiment scripts: machine info, CSV with '#' header comments."""
from __future__ import annotations

import csv
import datetime as _dt
import os
import platform
import subprocess
import sys
from typing import Dict, Iterable, List, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"


def machine_info() -> Dict[str, str]:
    import numpy
    import scipy

    return {
        "date_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "cpu_count": str(os.cpu_count()),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "git_commit": git_commit(),
    }


def write_csv(path: str, rows: Sequence[dict], columns: Sequence[str], header: Dict[str, str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        for k, v in header.items():
            f.write(f"# {k}: {v}\n")
        w = csv.DictWriter(f, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def read_csv(path: str) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def read_header(path: str) -> Dict[str, str]:
    out = {}
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if not ln.startswith("#"):
                break
            k, _, v = ln[1:].strip().partition(":")
            out[k.strip()] = v.strip()
    return out


def parse_int_list(spec: str) -> List[int]:
    """'1-5,8' -> [1,2,3,4,5,8]"""
    out: List[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out
