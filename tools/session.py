#!/usr/bin/env python3
"""The fastest-sort measurement session, natively on Windows (i7-13700F).

Three tests, four languages, the same 100 million signed 64-bit integers (splitmix64, seed 125, generated in each
program before any timing):
  1. each language's standard sort on one performance core,
  2. the same LSD radix sort (eight one-byte passes) written in each language, on one performance core,
  3. each language's parallel sort on all eight performance cores (logical CPUs 0-15).
Each cell is one process: it builds the input, then copies it into a work array and sorts it once as a warm-up and
RUNS more times, timing only the sort, checking the result is sorted and hashing it (FNV-1a over the 64-bit words).
Every cell in the session must produce the same hash.

Recorded rounds run each cell inside a pseudo-console (TICK=1: the program redraws the run and its elapsed seconds
every 100 ms) and save the screen as an asciinema cast. Rounds alternate the language order. A final plain round runs
without the recorder and the ticker, to check that recording didn't move the numbers.

usage: python tools/session.py RESULTS_DIR [ROUNDS=5]      (from the repo root)
env:   SORT_N (default 100000000), SORT_RUNS (default 5), BENCH_NO_GATE=1 (pilot only)
"""
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import psutil

ONE_CORE = "4"  # logical CPU 4: a performance core (0-15 are the eight P-cores with their SMT pairs, 16-23 E-cores)
P_CORES = "0-15"
GATE_CPUS = list(range(16))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PY = str(Path(sys.executable).with_name("python.exe"))
TOOLS = Path(__file__).resolve().parent
N = int(os.environ.get("SORT_N", "100000000"))
RUNS = int(os.environ.get("SORT_RUNS", "5"))
COLS, ROWS = 24, 4  # the program's lines are at most 22 characters, so the text stays big on a phone
JAVA = r"C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot\bin\java.exe"
LANGS = ("cpp", "rust", "go", "java")
TESTS = {1: ("std", ONE_CORE), 2: ("radix", ONE_CORE), 3: ("par", P_CORES)}


def ncpus(spec: str) -> int:
    lo, _, hi = spec.partition("-")
    return int(hi or lo) - int(lo) + 1


def argv_for(lang: str, mode: str, cpus: str, out: Path) -> tuple[list[str], dict]:
    threads = str(ncpus(cpus))
    args = [mode, str(N), str(RUNS), out.as_posix()]
    env = {}
    if lang == "cpp":
        cmd = ["cpp/build/sort.exe", *args]
    elif lang == "rust":
        cmd = ["rust/target/release/fastest_sort.exe", *args]
        env["RAYON_NUM_THREADS"] = threads
    elif lang == "go":
        cmd = ["go/fastestsort.exe", *args]
        # At least 2: with one P the recorder's ticker goroutine can only run by preempting the sort goroutine, which
        # cost the radix sort 18% in the first session; the other languages' tickers are plain OS threads. The
        # process stays pinned to the same one core either way.
        env["GOMAXPROCS"] = str(max(2, int(threads)))
    else:
        heap = "4g" if mode == "std" else "6g"
        cmd = [JAVA, f"-Xms{heap}", f"-Xmx{heap}", f"-XX:ActiveProcessorCount={threads}", "-cp", "java/classes", "Sort", *args]
    return [PY, str(TOOLS / "pin.py"), cpus, *cmd], env


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def quiet_gate(max_wait: int = 600) -> dict:
    """Waits until the P-cores are idle: mean under 5% and none over 15%, over 5 s. Gives up after max_wait."""
    if os.environ.get("BENCH_NO_GATE") == "1":
        return {"gate": "skipped"}
    waited = 0
    while True:
        per = psutil.cpu_percent(interval=5, percpu=True)
        mine = [per[c] for c in GATE_CPUS]
        reading = {"mean": round(sum(mine) / len(mine), 2), "max": max(mine), "total": round(sum(per) / len(per), 2)}
        if reading["mean"] < 5 and reading["max"] < 15:
            return reading
        if waited >= max_wait:
            raise RuntimeError(f"machine stayed busy for {max_wait} s: {reading}")
        if waited % 300 == 0:
            log(f"machine busy {reading}, waiting")
        waited += 5


ONLY = {c for c in os.environ.get("SORT_CELLS", "").split(",") if c}  # e.g. "go-std,go-radix" for a pilot


def order_for(round_no: int) -> list[tuple[int, str]]:
    langs = LANGS if round_no % 2 == 1 else tuple(reversed(LANGS))
    cells = [(test, lang) for test in TESTS for lang in langs]
    return [c for c in cells if not ONLY or f"{c[1]}-{TESTS[c[0]][0]}" in ONLY]


def run_cell(test: int, lang: str, rdir: Path, record: bool) -> dict:
    mode, cpus = TESTS[test]
    name = f"{lang}-{mode}"
    out = rdir / f"{name}.json"
    argv, extra = argv_for(lang, mode, cpus, out)
    env = dict(os.environ, **extra, TICK="1" if record else "0")
    busy = quiet_gate()
    t0 = time.time()
    if record:
        cmd = [PY, str(TOOLS / "cast.py"), str(rdir / f"{name}.cast"), str(COLS), str(ROWS), "--", *argv]
        rc = subprocess.call(cmd, env=env, creationflags=NO_WINDOW)
    else:
        rc = subprocess.call(argv, env=env, stdout=subprocess.DEVNULL, creationflags=NO_WINDOW)
    if rc != 0 or not out.exists():
        raise RuntimeError(f"{name}: exit {rc}")
    res = json.loads(out.read_text())
    if len(res["runs_s"]) != RUNS or res["n"] != N:
        raise RuntimeError(f"{name}: unexpected result {res}")
    return {"cell": name, "test": test, "lang": lang, "mode": mode, "cpus": cpus, **res, "busy_before": busy,
            "started": t0, "wall_s": time.time() - t0}


def versions() -> dict:
    def cmd(*a: str) -> str:
        p = subprocess.run(a, check=False, capture_output=True, text=True, creationflags=NO_WINDOW)
        return (p.stdout + p.stderr).strip()
    lock = Path("rust/Cargo.lock").read_text()
    rayon = lock.split('name = "rayon"\nversion = "', 1)[1].split('"', 1)[0]
    return {
        "clang": cmd(r"C:\Program Files\LLVM\bin\clang++.exe", "--version").splitlines()[0],
        "msvc_stl": Path("cpp/build/msvc.txt").read_text().strip() if Path("cpp/build/msvc.txt").exists() else "",
        "rustc": cmd(os.path.expanduser("~/.cargo/bin/rustc.exe"), "-vV"),
        "rayon": rayon,
        "go": cmd(r"C:\Program Files\Go\bin\go.exe", "version"),
        "java": cmd(JAVA, "-version"),
        "os": platform.platform(),
        "cpu": platform.processor(),
        "ram_bytes": psutil.virtual_memory().total,
        "power_plan": cmd("powercfg", "/getactivescheme"),
    }


def main() -> int:
    results = Path(sys.argv[1])
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    results.mkdir(parents=True, exist_ok=False)
    (results / "meta.json").write_text(json.dumps(
        {"versions": versions(), "rounds": rounds, "n": N, "runs_per_cell": RUNS, "one_core": ONE_CORE,
         "p_cores": P_CORES, "cols": COLS, "rows": ROWS, "started": time.ctime()}, indent=2))
    log("waiting for a quiet machine (up to 15 min)")
    quiet_gate(max_wait=900)
    hashes = set()
    for r in range(1, rounds + 2):
        record = r <= rounds
        rdir = results / (f"round{r}" if record else "plain")
        rdir.mkdir()
        log(f"round {r} ({'recorded' if record else 'plain'})")
        for test, lang in order_for(r):
            res = run_cell(test, lang, rdir, record)
            res["round"] = r if record else "plain"
            hashes.add(res["hash"])
            med = sorted(res["runs_s"])[len(res["runs_s"]) // 2]
            log(f"  {res['cell']:12s} median {med:.3f} s  (cpus seen {res['cpus_seen']}, wall {res['wall_s']:.0f} s)")
            with open(results / "runs.jsonl", "a") as f:
                f.write(json.dumps(res) + "\n")
            if len(hashes) != 1:
                raise RuntimeError(f"outputs differ: {hashes}")
    (results / "done").write_text(time.ctime() + "\n")
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
