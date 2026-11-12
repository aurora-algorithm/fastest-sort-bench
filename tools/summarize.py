#!/usr/bin/env python3
"""Medians of one session: every cell over all its recorded sorts, and the plain round next to it.

usage: python3 tools/summarize.py results/<session>   -> results/<session>/summary.json
"""

import json
import statistics
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    session = Path(sys.argv[1])
    lines = (session / "runs.jsonl").read_text().splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    if not rows:
        sys.exit(f"{session}: no runs")
    recorded = [r for r in rows if r["round"] != "plain"]
    plain = [r for r in rows if r["round"] == "plain"]
    cells = {}
    for name in dict.fromkeys(r["cell"] for r in recorded):
        runs = [t for r in recorded if r["cell"] == name for t in r["runs_s"]]
        plain_runs = [t for r in plain if r["cell"] == name for t in r["runs_s"]]
        median = statistics.median(runs)
        plain_median = statistics.median(plain_runs) if plain_runs else None
        cells[name] = {
            "test": next(r["test"] for r in recorded if r["cell"] == name),
            "median_s": round(median, 4),
            "min_s": round(min(runs), 4),
            "max_s": round(max(runs), 4),
            "runs": len(runs),
            "plain_median_s": round(plain_median, 4) if plain_median else None,
            "plain_vs_recorded": round(plain_median / median - 1, 4) if plain_median else None,
        }
    summary = {"session": session.name, "hashes": sorted({r["hash"] for r in rows}), "cells": cells}
    (session / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    for name, c in cells.items():
        print(f"{name:12s} {c['median_s']:.3f} s  n={c['runs']}  plain {c['plain_vs_recorded']:+.1%}")


if __name__ == "__main__":
    main()
