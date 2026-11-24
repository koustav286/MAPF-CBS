"""Shared matplotlib style: validated two-slot categorical palette, thin marks, quiet axes."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"
GRID = "#e4e3df"
# categorical slots 1-2 of the reference palette (validated: CVD dE 24.7, normal dE 33.6)
COLORS = {"cbs": "#2a78d6", "pp": "#eb6834"}
MARKERS = {"cbs": "o", "pp": "s"}
LABELS = {"cbs": "CBS", "pp": "PP"}
ALGS = ("cbs", "pp")


def setup() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT2, "axes.titlecolor": TEXT,
        "xtick.color": TEXT2, "ytick.color": TEXT2, "text.color": TEXT,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
        "lines.linewidth": 2, "lines.markersize": 5, "legend.frameon": False,
    })


def end_label(ax, x, y, alg) -> None:
    """Direct label at the end of a line, in text ink next to the coloured mark."""
    ax.annotate(LABELS[alg], (x, y), xytext=(5, 0), textcoords="offset points",
                va="center", fontsize=9, color=TEXT2)


def end_labels(ax, points) -> None:
    """Direct labels for several lines ({alg: (x, y)}), nudged apart so they never overlap:
    the line ending higher gets its label above, the lower one below."""
    pts = [(alg, x, y) for alg, (x, y) in points.items() if y == y]  # drop NaN
    pts.sort(key=lambda t: t[2])
    n = len(pts)
    for rank, (alg, x, y) in enumerate(pts):
        dy = 0 if n == 1 else (-7 if rank == 0 else 7)
        ax.annotate(LABELS[alg], (x, y), xytext=(5, dy), textcoords="offset points",
                    va="center", fontsize=9, color=TEXT2)


def solid_legend(ax, **kw):
    leg = ax.legend(**kw)
    for h in leg.legend_handles:
        h.set_alpha(1)
    return leg
