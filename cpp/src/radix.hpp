#pragma once
#include <cstdint>
#include <utility>
#include <vector>

// LSD radix sort: eight passes, one byte each, lowest byte first. It never compares two numbers.
// Flipping the sign bit makes negative numbers sort before positive ones.
inline void radix_sort(std::vector<int64_t>& a, std::vector<int64_t>& buf) {
  constexpr uint64_t SIGN = 1ULL << 63;
  static uint64_t count[8][256];
  for (auto& pass : count) for (auto& c : pass) c = 0;
  for (int64_t x : a) {
    uint64_t u = static_cast<uint64_t>(x) ^ SIGN;
    for (int p = 0; p < 8; ++p) count[p][(u >> (8 * p)) & 255]++;
  }
  int64_t* src = a.data();
  int64_t* dst = buf.data();
  for (int p = 0; p < 8; ++p) {
    uint64_t pos[256];
    uint64_t sum = 0;
    for (int d = 0; d < 256; ++d) { pos[d] = sum; sum += count[p][d]; }
    for (size_t i = 0; i < a.size(); ++i) {
      uint64_t u = static_cast<uint64_t>(src[i]) ^ SIGN;
      dst[pos[(u >> (8 * p)) & 255]++] = src[i];
    }
    std::swap(src, dst);
  }
}
