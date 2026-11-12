/** LSD radix sort: eight passes, one byte each, lowest byte first. It never compares two numbers.
 *  Flipping the sign bit makes negative numbers sort before positive ones. */
final class Radix {
    static void radixSort(long[] a, long[] buf) {
        final long SIGN = 1L << 63;
        int[][] count = new int[8][256];
        for (long x : a) {
            long u = x ^ SIGN;
            for (int p = 0; p < 8; p++) count[p][(int) ((u >>> (8 * p)) & 255)]++;
        }
        long[] src = a, dst = buf;
        for (int p = 0; p < 8; p++) {
            int[] pos = new int[256];
            int sum = 0;
            for (int d = 0; d < 256; d++) { pos[d] = sum; sum += count[p][d]; }
            for (long x : src) {
                int d = (int) (((x ^ SIGN) >>> (8 * p)) & 255);
                dst[pos[d]++] = x;
            }
            long[] t = src; src = dst; dst = t;
        }
    }
}
