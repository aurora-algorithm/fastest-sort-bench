# Sorting 100 million numbers in C++, Rust, Go and Java

Code and per-run results behind the "Fastest sorting algorithm? C++ vs Rust vs Go vs Java on 100 million numbers, best 0.36 s" Short.

## What is tested
Every program (`cpp/src/sort.cpp`, `rust/src/main.rs`, `go/main.go`, `java/Sort.java`) takes `MODE N RUNS OUT.json`:

- builds N signed 64-bit numbers with splitmix64 from seed 125 (the same numbers in all four);
- copies them into a work array and sorts once as a warm-up, then RUNS more times, timing only the sort call;
- checks each result is sorted and hashes it (FNV-1a over the 64-bit words); the hash must not change between runs;
- writes `{"lang","mode","n","cpus_seen","hash","warmup_s","runs_s":[...]}`.

| Test | MODE | Cores | C++ | Rust | Go | Java |
|---|---|---|---|---|---|---|
| 1 | `std` | 1 | `std::sort` | `sort_unstable` | `slices.Sort` | `Arrays.sort` |
| 2 | `radix` | 1 | `radix.hpp` | `radix.rs` | `radix.go` | `Radix.java` |
| 3 | `par` | 8 performance cores | `std::sort(std::execution::par, ...)` | rayon `par_sort_unstable` | `parallel.go` | `Arrays.parallelSort` |

The radix sort is the same LSD algorithm in every language: one counting pass for all eight byte histograms, then
eight scatter passes of one byte each, lowest byte first, with the sign bit flipped so negatives sort first. Buffers
are allocated before timing (Java's `parallelSort` allocates its own merge buffer inside the call, as the library
does). Go's standard library has no parallel sort, so `parallel.go` is our own goroutine version.

## Setup
- **Machine:** Intel i7-13700F PC, 32 GB, Windows 11 (10.0.26200), Balanced power plan, native (no containers).
- **Versions** (`results/fastest-sort-i7-20261109b/meta.json`): clang 23.1.5 with MSVC's standard library
  14.38.33130, rustc 1.99.1 (LLVM 23.1.1), rayon 1.12.0, Go 1.27.3, Temurin 25.0.5.
- **Builds** (`build.cmd`): CMake Release with `-march=native` for C++, `cargo build --release` with
  `-C target-cpu=native` (`rust/.cargo/config.toml`), `go build`, `javac`.
- **Pinning:** `std` and `radix` run pinned to logical CPU 4 (one performance core). `par` runs on CPUs 0-15 (the 8
  performance cores and their SMT threads) with `RAYON_NUM_THREADS=16`, `GOMAXPROCS=16` and
  `-XX:ActiveProcessorCount=16`; C++ uses the MSVC parallel algorithms' thread pool inside the same mask. On one core
  Go runs with `GOMAXPROCS=2`, so the screen ticker goroutine does not have to preempt the sort.
- **Java heap:** `-Xms4g -Xmx4g` for `std`, `-Xms6g -Xmx6g` for `radix` and `par`.
- **Quiet machine:** before each cell the script waits until CPUs 0-15 average under 5% with none over 15% (5 s sample).
- **Runs:** 5 recorded rounds (the language order flips every round), each cell 1 warm-up + 5 timed sorts, so 25 sorts
  per cell. The live screen is recorded as an asciinema cast (`round*/*.cast`). Then 1 plain round without recorder
  or ticker. Every cell produced the same output hash, `e8a1b92a779c5685`.

## Results (median of 25 sorts, `results/fastest-sort-i7-20261109b/summary.json`)
| Test | C++ | Rust | Go | Java |
|---|---|---|---|---|
| 1, built-in sort, 1 core | 7.727 s | 1.561 s | 7.504 s | 6.373 s |
| 2, same radix sort, 1 core | 1.119 s | 1.151 s | 1.543 s | 1.316 s |
| 3, parallel sort, 8 cores | 1.113 s | 0.358 s | 1.196 s | 0.733 s |

The plain round is within 1.7% of the recorded medians for every cell (`plain_vs_recorded` in the same file). Every
sort's time is in `runs.jsonl` and in `round*/<cell>.json`.

## Reproduce
On Windows 11 with Visual Studio 2022's C++ build tools, LLVM for Windows, CMake, Ninja, Rust (MSVC toolchain), Go,
Temurin JDK 25 and Python 3 with `psutil` and `pywinpty`:

```bash
cmd //c build.cmd
python tools/session.py results/<name> 5      # SORT_N and SORT_RUNS override the size and runs per cell
python3 tools/summarize.py results/<name>
```

`tools/session.py` expects Java at `C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot` (`JAVA` in the script).

## Notes
- Test 1 uses each language's stock built-in sort. For C++ that is `std::sort` from MSVC's standard library, built
  with clang.
- Go's parallel sort is our code, not a library sort.
- The numbers are uniform random 64-bit integers.
