//! Sorts N 64-bit integers RUNS times (after one warm-up) and reports each sort's time.
//! usage: fastest_sort MODE N RUNS OUT.json      MODE = std | radix | par
//! The input is the same in every language: splitmix64 from seed 125, read as signed 64-bit.
mod radix;

use rayon::prelude::*;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

fn make_input(n: usize) -> Vec<i64> {
    let mut state: u64 = 125;
    (0..n)
        .map(|_| {
            state = state.wrapping_add(0x9e3779b97f4a7c15);
            let mut z = state;
            z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
            (z ^ (z >> 31)) as i64
        })
        .collect()
}

fn fnv(v: &[i64]) -> u64 {
    v.iter().fold(0xcbf29ce484222325u64, |h, &x| (h ^ x as u64).wrapping_mul(0x100000001b3))
}

/// Live screen for the recording (TICK=1): the run being timed and its elapsed seconds, redrawn every 100 ms.
struct Ticker {
    state: Arc<Mutex<Option<(String, Instant)>>>,
    stop: Arc<AtomicBool>,
    thread: Option<std::thread::JoinHandle<()>>,
}

impl Ticker {
    fn new(on: bool) -> Self {
        let state = Arc::new(Mutex::new(None::<(String, Instant)>));
        let stop = Arc::new(AtomicBool::new(false));
        let thread = on.then(|| {
            let (state, stop) = (state.clone(), stop.clone());
            std::thread::spawn(move || {
                while !stop.load(Ordering::Relaxed) {
                    std::thread::sleep(Duration::from_millis(100));
                    let g = state.lock().unwrap();
                    if let Some((label, t0)) = g.as_ref() {
                        print!("\r{:<8}sorting {:.1} s", label, t0.elapsed().as_secs_f64());
                        std::io::stdout().flush().unwrap();
                    }
                }
            })
        });
        Ticker { state, stop, thread }
    }
    fn start(&self, label: &str) {
        *self.state.lock().unwrap() = Some((label.to_string(), Instant::now()));
    }
    fn done(&self, label: &str, s: f64) {
        let mut g = self.state.lock().unwrap();
        *g = None;
        println!("\r{:<10}{:>5.2} s     ", label, s);
        std::io::stdout().flush().unwrap();
    }
}

impl Drop for Ticker {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        if let Some(t) = self.thread.take() {
            t.join().unwrap();
        }
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 5 {
        eprintln!("usage: fastest_sort std|radix|par N RUNS OUT.json");
        std::process::exit(2);
    }
    let mode = args[1].as_str();
    let n: usize = args[2].parse().expect("N");
    let runs: usize = args[3].parse().expect("RUNS");
    if !["std", "radix", "par"].contains(&mode) {
        eprintln!("unknown mode {mode}");
        std::process::exit(2);
    }
    let ticker = Ticker::new(std::env::var("TICK").as_deref() == Ok("1"));

    let input = make_input(n);
    let mut work = vec![0i64; n];
    let mut buffer = vec![0i64; if mode == "radix" { n } else { 0 }];
    let (mut warmup, mut times, mut hash) = (0.0, Vec::new(), 0u64);
    for k in 0..=runs {
        work.copy_from_slice(&input);
        let label = if k == 0 { "warm-up".to_string() } else { format!("run {k}") };
        ticker.start(&label);
        let t0 = Instant::now();
        match mode {
            "std" => work.sort_unstable(),
            "par" => work.par_sort_unstable(),
            _ => radix::radix_sort(&mut work, &mut buffer),
        }
        let s = t0.elapsed().as_secs_f64();
        ticker.done(&label, s);
        if !work.is_sorted() {
            eprintln!("not sorted");
            std::process::exit(1);
        }
        let h = fnv(&work);
        if k > 0 && h != hash {
            eprintln!("hash changed between runs");
            std::process::exit(1);
        }
        hash = h;
        if k == 0 { warmup = s } else { times.push(s) }
    }
    drop(ticker);

    let runs_s: Vec<String> = times.iter().map(|t| format!("{t:.6}")).collect();
    let json = format!(
        "{{\"lang\":\"rust\",\"mode\":\"{mode}\",\"n\":{n},\"cpus_seen\":{},\"hash\":\"{hash:016x}\",\"warmup_s\":{warmup:.6},\"runs_s\":[{}]}}\n",
        rayon::current_num_threads(),
        runs_s.join(",")
    );
    std::fs::write(&args[4], json).expect("write OUT.json");
}
