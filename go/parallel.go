package main

import (
	"runtime"
	"slices"
	"sync"
)

// parallelSort is what Go programs write for this, since the standard library has no parallel sort: one chunk per
// GOMAXPROCS, each sorted by slices.Sort in its own goroutine, then neighbouring chunks merged pairwise, in
// parallel, until one run is left. buf must be as long as a.
func parallelSort(a, buf []int64) {
	parts := runtime.GOMAXPROCS(0)
	bounds := make([]int, parts+1)
	for i := range bounds {
		bounds[i] = len(a) * i / parts
	}
	var wg sync.WaitGroup
	for i := 0; i < parts; i++ {
		wg.Add(1)
		go func(lo, hi int) {
			defer wg.Done()
			slices.Sort(a[lo:hi])
		}(bounds[i], bounds[i+1])
	}
	wg.Wait()
	src, dst := a, buf
	for len(bounds) > 2 {
		next := []int{0}
		for i := 0; i+1 < len(bounds); i += 2 {
			lo := bounds[i]
			if i+2 < len(bounds) {
				mid, hi := bounds[i+1], bounds[i+2]
				wg.Add(1)
				go func() {
					defer wg.Done()
					merge(dst[lo:hi], src[lo:mid], src[mid:hi])
				}()
				next = append(next, hi)
			} else {
				hi := bounds[i+1]
				copy(dst[lo:hi], src[lo:hi])
				next = append(next, hi)
			}
		}
		wg.Wait()
		bounds = next
		src, dst = dst, src
	}
	if &src[0] != &a[0] {
		copy(a, src)
	}
}

func merge(out, x, y []int64) {
	i, j, k := 0, 0, 0
	for i < len(x) && j < len(y) {
		if y[j] < x[i] {
			out[k] = y[j]
			j++
		} else {
			out[k] = x[i]
			i++
		}
		k++
	}
	k += copy(out[k:], x[i:])
	copy(out[k:], y[j:])
}
