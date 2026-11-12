#!/usr/bin/env python3
"""Runs a command pinned to a set of logical CPUs; on Windows the command's own children and threads inherit the mask.

usage: python pin.py CPUS COMMAND...      CPUS = "4" or "0-15"
"""
import subprocess
import sys

import psutil


def cpus(spec: str) -> list[int]:
    lo, _, hi = spec.partition("-")
    return list(range(int(lo), int(hi or lo) + 1))


def main() -> int:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    psutil.Process().cpu_affinity(cpus(sys.argv[1]))
    return subprocess.call(sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
