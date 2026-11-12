@echo off
rem Builds every side natively on Windows: clang++ (LLVM) against the MSVC runtime and STL, cargo release, go build, javac.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set PATH=C:\Program Files\LLVM\bin;C:\Program Files\CMake\bin;C:\Program Files\Go\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%USERPROFILE%\.cargo\bin;C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot\bin;%PATH%
cd /d "%~dp0"
cmake -S cpp -B cpp\build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ || exit /b 1
cmake --build cpp\build || exit /b 1
echo MSVC %VCToolsVersion%> cpp\build\msvc.txt
cd rust
cargo build --release || exit /b 1
cd ..\go
go build -o fastestsort.exe . || exit /b 1
cd ..\java
if not exist classes mkdir classes
javac -d classes Sort.java Radix.java || exit /b 1
echo build ok
