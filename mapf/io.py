"""Parsers for Moving AI ``.map`` and ``.scen`` files.

Coordinate convention: Moving AI scenario columns are ``start_x start_y goal_x goal_y`` where
x is the column and y is the row. Internally everything is (row, col).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

from .grid import Cell, Grid

PASSABLE = set(".GS")  # '@', 'O', 'T', 'W' (and anything else) are blocked


def parse_map(path: str) -> Grid:
    with open(path, "r", encoding="ascii") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
    header = {}
    i = 0
    while i < len(lines) and lines[i].strip() != "map":
        parts = lines[i].split()
        if len(parts) == 2:
            header[parts[0]] = parts[1]
        i += 1
    if i == len(lines):
        raise ValueError(f"{path}: missing 'map' line")
    h, w = int(header["height"]), int(header["width"])
    rows = lines[i + 1 : i + 1 + h]
    if len(rows) != h or any(len(r) < w for r in rows):
        raise ValueError(f"{path}: grid does not match height {h} / width {w}")
    passable = [[ch in PASSABLE for ch in row[:w]] for row in rows]
    name = os.path.splitext(os.path.basename(path))[0]
    return Grid(passable, name=name)


@dataclass(frozen=True)
class ScenEntry:
    bucket: int
    map_name: str
    width: int
    height: int
    start: Cell  # (row, col)
    goal: Cell  # (row, col)
    optimal_length: float


def parse_scen(path: str) -> List[ScenEntry]:
    out: List[ScenEntry] = []
    with open(path, "r", encoding="ascii") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("version"):
                continue
            p = ln.split("\t") if "\t" in ln else ln.split()
            if len(p) != 9:
                raise ValueError(f"{path}: bad scen row {ln!r}")
            sx, sy, gx, gy = int(p[4]), int(p[5]), int(p[6]), int(p[7])
            out.append(
                ScenEntry(
                    bucket=int(p[0]),
                    map_name=p[1],
                    width=int(p[2]),
                    height=int(p[3]),
                    start=(sy, sx),
                    goal=(gy, gx),
                    optimal_length=float(p[8]),
                )
            )
    return out


def scen_path(data_dir: str, map_name: str, scen_id: int) -> str:
    return os.path.join(data_dir, "scens", f"{map_name}-random-{scen_id}.scen")


def map_path(data_dir: str, map_name: str) -> str:
    return os.path.join(data_dir, "maps", f"{map_name}.map")


def load_instance(data_dir: str, map_name: str, scen_id: int, k: int) -> Tuple[Grid, List[Cell], List[Cell]]:
    """Grid plus the starts/goals of the first ``k`` agents of a random scenario file."""
    grid = parse_map(map_path(data_dir, map_name))
    entries = parse_scen(scen_path(data_dir, map_name, scen_id))
    if k > len(entries):
        raise ValueError(f"scenario has only {len(entries)} agents, asked for {k}")
    entries = entries[:k]
    return grid, [e.start for e in entries], [e.goal for e in entries]
