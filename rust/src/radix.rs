/// LSD radix sort: eight passes, one byte each, lowest byte first. It never compares two numbers.
/// Flipping the sign bit makes negative numbers sort before positive ones.
pub fn radix_sort(a: &mut [i64], buf: &mut [i64]) {
    const SIGN: u64 = 1 << 63;
    let mut count = [[0usize; 256]; 8];
    for &x in a.iter() {
        let u = (x as u64) ^ SIGN;
        for p in 0..8 {
            count[p][((u >> (8 * p)) & 255) as usize] += 1;
        }
    }
    let (mut src, mut dst) = (a, buf);
    for p in 0..8 {
        let mut pos = [0usize; 256];
        let mut sum = 0;
        for d in 0..256 {
            pos[d] = sum;
            sum += count[p][d];
        }
        for i in 0..src.len() {
            let u = (src[i] as u64) ^ SIGN;
            let d = ((u >> (8 * p)) & 255) as usize;
            dst[pos[d]] = src[i];
            pos[d] += 1;
        }
        std::mem::swap(&mut src, &mut dst);
    }
}
