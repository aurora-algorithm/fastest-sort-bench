package main

// radixSort is an LSD radix sort: eight passes, one byte each, lowest byte first. It never compares two numbers.
// Flipping the sign bit makes negative numbers sort before positive ones.
func radixSort(a, buf []int64) {
	const sign = uint64(1) << 63
	var count [8][256]int
	for _, x := range a {
		u := uint64(x) ^ sign
		for p := 0; p < 8; p++ {
			count[p][(u>>(8*p))&255]++
		}
	}
	src, dst := a, buf
	for p := 0; p < 8; p++ {
		var pos [256]int
		sum := 0
		for d := 0; d < 256; d++ {
			pos[d] = sum
			sum += count[p][d]
		}
		for _, x := range src {
			d := ((uint64(x) ^ sign) >> (8 * p)) & 255
			dst[pos[d]] = x
			pos[d]++
		}
		src, dst = dst, src
	}
}
