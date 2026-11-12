cmake_minimum_required(VERSION 3.24)
project(fastest_sort CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
# Release = -O3 -DNDEBUG. Every compiled side builds for the CPU it runs on (Rust: target-cpu=native in rust/.cargo).
set(BENCH_ARCH_FLAGS "-march=native" CACHE STRING "CPU flags")

add_executable(sort src/sort.cpp)
target_compile_options(sort PRIVATE ${BENCH_ARCH_FLAGS})
