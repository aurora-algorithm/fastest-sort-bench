// Sorts N 64-bit integers RUNS times (after one warm-up) and reports each sort's time.
// usage: fastestsort MODE N RUNS OUT.json      MODE = std | radix | par
// The input is the same in every language: splitmix64 from seed 125, read as signed 64-bit.
package main

import (
	"fmt"
	"os"
	"runtime"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"
)

func makeInput(n int) []int64 {
	v := make([]int64, n)
	state := uint64(125)
	for i := range v {
		state += 0x9e3779b97f4a7c15
		z := state
		z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9
		z = (z ^ (z >> 27)) * 0x94d049bb133111eb
		v[i] = int64(z ^ (z >> 31))
	}
	return v
}

func fnv(v []int64) uint64 {
	h := uint64(0xcbf29ce484222325)
	for _, x := range v {
		h = (h ^ uint64(x)) * 0x100000001b3
	}
	return h
}

// ticker is the live screen for the recording (TICK=1): the run being timed and its elapsed seconds, redrawn
// every 100 ms.
type ticker struct {
	mu      sync.Mutex
	label   string
	t0      time.Time
	running bool
}

func newTicker(on bool) *ticker {
	t := &ticker{}
	if on {
		go func() {
			for {
				time.Sleep(100 * time.Millisecond)
				t.mu.Lock()
				if t.running {
					fmt.Printf("\r%-8ssorting %.1f s", t.label, time.Since(t.t0).Seconds())
				}
				t.mu.Unlock()
			}
		}()
	}
	return t
}

func (t *ticker) start(label string) {
	t.mu.Lock()
	t.label, t.t0, t.running = label, time.Now(), true
	t.mu.Unlock()
}

func (t *ticker) done(label string, s float64) {
	t.mu.Lock()
	t.running = false
	fmt.Printf("\r%-10s%5.2f s     \n", label, s)
	t.mu.Unlock()
}

func fail(msg string, code int) {
	fmt.Fprintln(os.Stderr, msg)
	os.Exit(code)
}

func main() {
	if len(os.Args) != 5 {
		fail("usage: fastestsort std|radix|par N RUNS OUT.json", 2)
	}
	mode := os.Args[1]
	n, err := strconv.Atoi(os.Args[2])
	if err != nil {
		fail("N: "+err.Error(), 2)
	}
	runs, err := strconv.Atoi(os.Args[3])
	if err != nil {
		fail("RUNS: "+err.Error(), 2)
	}
	if mode != "std" && mode != "radix" && mode != "par" {
		fail("unknown mode "+mode, 2)
	}
	tick := newTicker(os.Getenv("TICK") == "1")

	input := makeInput(n)
	work := make([]int64, n)
	var buffer []int64
	if mode != "std" {
		buffer = make([]int64, n)
	}
	var warmup float64
	var times []string
	var hash uint64
	for k := 0; k <= runs; k++ {
		copy(work, input)
		label := "warm-up"
		if k > 0 {
			label = fmt.Sprintf("run %d", k)
		}
		tick.start(label)
		t0 := time.Now()
		switch mode {
		case "std":
			slices.Sort(work)
		case "par":
			parallelSort(work, buffer)
		default:
			radixSort(work, buffer)
		}
		s := time.Since(t0).Seconds()
		tick.done(label, s)
		if !slices.IsSorted(work) {
			fail("not sorted", 1)
		}
		h := fnv(work)
		if k > 0 && h != hash {
			fail("hash changed between runs", 1)
		}
		hash = h
		if k == 0 {
			warmup = s
		} else {
			times = append(times, fmt.Sprintf("%.6f", s))
		}
	}

	json := fmt.Sprintf(`{"lang":"go","mode":"%s","n":%d,"cpus_seen":%d,"hash":"%016x","warmup_s":%.6f,"runs_s":[%s]}`+"\n",
		mode, n, runtime.GOMAXPROCS(0), hash, warmup, strings.Join(times, ","))
	if err := os.WriteFile(os.Args[4], []byte(json), 0o644); err != nil {
		fail("write OUT.json: "+err.Error(), 1)
	}
}
