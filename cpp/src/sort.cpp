// Sorts N 64-bit integers RUNS times (after one warm-up) and reports each sort's time.
// usage: sort MODE N RUNS OUT.json      MODE = std | radix | par
// The input is the same in every language: splitmix64 from seed 125, read as signed 64-bit.
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <execution>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "radix.hpp"

namespace {

std::vector<int64_t> make_input(size_t n) {
  std::vector<int64_t> v(n);
  uint64_t state = 125;
  for (auto& x : v) {
    uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    x = static_cast<int64_t>(z ^ (z >> 31));
  }
  return v;
}

uint64_t fnv(const std::vector<int64_t>& v) {
  uint64_t h = 0xcbf29ce484222325ULL;
  for (int64_t x : v) h = (h ^ static_cast<uint64_t>(x)) * 0x100000001b3ULL;
  return h;
}

// Live screen for the recording (TICK=1): the run being timed and its elapsed seconds, redrawn every 100 ms.
class Ticker {
 public:
  explicit Ticker(bool on) : on_(on) {
    if (on_) thread_ = std::thread([this] { loop(); });
  }
  ~Ticker() {
    stop_ = true;
    if (thread_.joinable()) thread_.join();
  }
  void start(const std::string& label) {
    std::lock_guard<std::mutex> g(mu_);
    label_ = label;
    t0_ = std::chrono::steady_clock::now();
    running_ = true;
  }
  void done(const std::string& label, double s) {
    std::lock_guard<std::mutex> g(mu_);
    running_ = false;
    std::printf("\r%-10s%5.2f s     \n", label.c_str(), s);
    std::fflush(stdout);
  }

 private:
  void loop() {
    while (!stop_) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
      std::lock_guard<std::mutex> g(mu_);
      if (!running_) continue;
      double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0_).count();
      std::printf("\r%-8ssorting %.1f s", label_.c_str(), s);
      std::fflush(stdout);
    }
  }
  bool on_;
  std::atomic<bool> stop_{false};
  std::mutex mu_;
  std::string label_;
  std::chrono::steady_clock::time_point t0_;
  bool running_ = false;
  std::thread thread_;
};

}  // namespace

int main(int argc, char** argv) {
  if (argc != 5) {
    std::fprintf(stderr, "usage: sort std|radix|par N RUNS OUT.json\n");
    return 2;
  }
  const std::string mode = argv[1];
  const size_t n = std::strtoull(argv[2], nullptr, 10);
  const int runs = std::atoi(argv[3]);
  if (mode != "std" && mode != "radix" && mode != "par") {
    std::fprintf(stderr, "unknown mode %s\n", mode.c_str());
    return 2;
  }
  const char* tick = std::getenv("TICK");
  Ticker ticker(tick && std::string(tick) == "1");

  const std::vector<int64_t> input = make_input(n);
  std::vector<int64_t> work(n);
  std::vector<int64_t> buffer(mode == "radix" ? n : 0);
  std::vector<double> times;
  double warmup = 0;
  uint64_t hash = 0;
  for (int k = 0; k <= runs; ++k) {
    std::copy(input.begin(), input.end(), work.begin());
    const std::string label = k == 0 ? "warm-up" : "run " + std::to_string(k);
    ticker.start(label);
    auto t0 = std::chrono::steady_clock::now();
    if (mode == "std") {
      std::sort(work.begin(), work.end());
    } else if (mode == "par") {
#ifdef __cpp_lib_parallel_algorithm
      std::sort(std::execution::par, work.begin(), work.end());
#else
      std::fprintf(stderr, "this standard library has no std::execution::par\n");
      return 2;
#endif
    } else {
      radix_sort(work, buffer);
    }
    double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    ticker.done(label, s);
    if (!std::is_sorted(work.begin(), work.end())) {
      std::fprintf(stderr, "not sorted\n");
      return 1;
    }
    uint64_t h = fnv(work);
    if (k > 0 && h != hash) {
      std::fprintf(stderr, "hash changed between runs\n");
      return 1;
    }
    hash = h;
    if (k == 0) warmup = s; else times.push_back(s);
  }

  FILE* out = std::fopen(argv[4], "w");
  if (!out) {
    std::fprintf(stderr, "cannot write %s\n", argv[4]);
    return 1;
  }
  std::fprintf(out, "{\"lang\":\"cpp\",\"mode\":\"%s\",\"n\":%zu,\"cpus_seen\":%u,\"hash\":\"%016llx\",\"warmup_s\":%.6f,\"runs_s\":[",
               mode.c_str(), n, std::thread::hardware_concurrency(), static_cast<unsigned long long>(hash), warmup);
  for (size_t i = 0; i < times.size(); ++i) std::fprintf(out, "%s%.6f", i ? "," : "", times[i]);
  std::fprintf(out, "]}\n");
  std::fclose(out);
  return 0;
}
