"""Paste generated result files into README.md between marker comments.

    <!-- BEGIN results/summary.md -->
    ... replaced ...
    <!-- END results/summary.md -->

The first heading of each pasted file is dropped and the others are demoted two levels so they
nest under the README section. Numbers in the README therefore always come from the CSVs.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def demote(md: str) -> str:
    lines = md.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    out = []
    for ln in lines:
        m = re.match(r"^(#+) (.*)$", ln)
        out.append(("#" * min(6, len(m.group(1)) + 2) + " " + m.group(2)) if m else ln)
    return "\n".join(out).strip()


def main() -> int:
    path = os.path.join(ROOT, "README.md")
    text = open(path, encoding="utf-8").read()
    pat = re.compile(r"(<!-- BEGIN (\S+) -->\n)(.*?)(<!-- END \2 -->)", re.S)

    def repl(m):
        src = os.path.join(ROOT, m.group(2))
        if not os.path.exists(src):
            print(f"warning: {m.group(2)} missing, block left unchanged", file=sys.stderr)
            return m.group(0)
        return m.group(1) + demote(open(src, encoding="utf-8").read()) + "\n" + m.group(4)

    new, n = pat.subn(repl, text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"updated {n} block(s) in README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
