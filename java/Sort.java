import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

/** Sorts N 64-bit integers RUNS times (after one warm-up) and reports each sort's time.
 *  usage: java Sort MODE N RUNS OUT.json      MODE = std | radix | par
 *  The input is the same in every language: splitmix64 from seed 125, read as signed 64-bit. */
public final class Sort {
    static long[] makeInput(int n) {
        long[] v = new long[n];
        long state = 125;
        for (int i = 0; i < n; i++) {
            state += 0x9e3779b97f4a7c15L;
            long z = state;
            z = (z ^ (z >>> 30)) * 0xbf58476d1ce4e5b9L;
            z = (z ^ (z >>> 27)) * 0x94d049bb133111ebL;
            v[i] = z ^ (z >>> 31);
        }
        return v;
    }

    static long fnv(long[] v) {
        long h = 0xcbf29ce484222325L;
        for (long x : v) h = (h ^ x) * 0x100000001b3L;
        return h;
    }

    static boolean isSorted(long[] v) {
        for (int i = 1; i < v.length; i++) if (v[i - 1] > v[i]) return false;
        return true;
    }

    /** Live screen for the recording (TICK=1): the run being timed and its elapsed seconds, redrawn every 100 ms. */
    static final class Ticker {
        private String label;
        private long t0;
        private boolean running;

        Ticker(boolean on) {
            if (!on) return;
            Thread t = new Thread(() -> {
                while (true) {
                    try { Thread.sleep(100); } catch (InterruptedException e) { return; }
                    synchronized (this) {
                        if (running) {
                            System.out.printf(Locale.ROOT, "\r%-8ssorting %.1f s", label, (System.nanoTime() - t0) / 1e9);
                            System.out.flush();
                        }
                    }
                }
            });
            t.setDaemon(true);
            t.start();
        }

        synchronized void start(String l) { label = l; t0 = System.nanoTime(); running = true; }

        synchronized void done(String l, double s) {
            running = false;
            System.out.printf(Locale.ROOT, "\r%-10s%5.2f s     %n", l, s);
            System.out.flush();
        }
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 4) { System.err.println("usage: java Sort std|radix|par N RUNS OUT.json"); System.exit(2); }
        String mode = args[0];
        int n = Integer.parseInt(args[1]);
        int runs = Integer.parseInt(args[2]);
        if (!Arrays.asList("std", "radix", "par").contains(mode)) { System.err.println("unknown mode " + mode); System.exit(2); }
        Ticker ticker = new Ticker("1".equals(System.getenv("TICK")));

        long[] input = makeInput(n);
        long[] work = new long[n];
        long[] buffer = new long["radix".equals(mode) ? n : 0];
        double warmup = 0;
        List<String> times = new ArrayList<>();
        long hash = 0;
        for (int k = 0; k <= runs; k++) {
            System.arraycopy(input, 0, work, 0, n);
            String label = k == 0 ? "warm-up" : "run " + k;
            ticker.start(label);
            long t0 = System.nanoTime();
            switch (mode) {
                case "std": Arrays.sort(work); break;
                case "par": Arrays.parallelSort(work); break;
                default: Radix.radixSort(work, buffer);
            }
            double s = (System.nanoTime() - t0) / 1e9;
            ticker.done(label, s);
            if (!isSorted(work)) { System.err.println("not sorted"); System.exit(1); }
            long h = fnv(work);
            if (k > 0 && h != hash) { System.err.println("hash changed between runs"); System.exit(1); }
            hash = h;
            if (k == 0) warmup = s; else times.add(String.format(Locale.ROOT, "%.6f", s));
        }

        String json = String.format(Locale.ROOT, "{\"lang\":\"java\",\"mode\":\"%s\",\"n\":%d,\"cpus_seen\":%d,\"hash\":\"%016x\",\"warmup_s\":%.6f,\"runs_s\":[%s]}%n",
                mode, n, Runtime.getRuntime().availableProcessors(), hash, warmup, String.join(",", times));
        Files.write(Paths.get(args[3]), json.getBytes(StandardCharsets.UTF_8));
    }
}
