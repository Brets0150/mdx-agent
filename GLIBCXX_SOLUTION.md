# GLIBCXX Version Compatibility - Complete Analysis and Solution

## The Problem

When deploying the cracker binary to systems with older glibc versions, you may encounter:

```
/lib/x86_64-linux-gnu/libstdc++.so.6: version `GLIBCXX_3.4.32' not found
```

## Root Cause Analysis

### Why Static Linking Doesn't Work

The cracker binary depends on Qt5Core, which is a **shared library** (`.so` file). Qt5Core.so itself has dynamic dependencies on:

- `libstdc++.so.6` (C++ standard library)
- `libgcc_s.so.1` (GCC runtime library)

When we link our binary:
```
g++ -static-libstdc++ -static-libgcc -o cracker ... libQt5Core.so
```

Even with `-static-libstdc++` and `-static-libgcc` flags, the binary STILL has dynamic dependencies because:

1. Qt5Core.so brings in its own dynamic dependencies
2. The dynamic linker resolves Qt5Core's dependencies at runtime
3. Those dependencies override our static linking attempts

**Verification:**
```bash
$ ldd /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 | grep libstdc
libstdc++.so.6 => /lib/x86_64-linux-gnu/libstdc++.so.6

$ ldd ./cracker | grep libstdc
libstdc++.so.6 => /lib/x86_64-linux-gnu/libstdc++.so.6
```

The libstdc++ dependency comes FROM Qt5Core, not from our code.

### Why Bundling libstdc++ Also Doesn't Work

If we bundle `libstdc++.so.6` in the package and set `LD_LIBRARY_PATH`, we hit another problem:

**Hashtopolis calls the binary directly**, not through a launcher script:
```bash
# What Hashtopolis does:
/path/to/cracker.bin crack -a hashes.txt ...

# NOT this:
/path/to/cracker crack -a hashes.txt ...  # (launcher script)
```

Since `LD_LIBRARY_PATH` is set by the launcher script, calling `cracker.bin` directly bypasses it.

## Solutions (In Order of Preference)

### Solution 1: Build on an Older System ⭐ RECOMMENDED

Build the cracker on a system with **older GLIBC/GLIBCXX** that's compatible with your target deployment environment.

**Build System Requirements:**
- Ubuntu 20.04 LTS (GLIBCXX_3.4.28)
- Debian 10 (GLIBCXX_3.4.26)
- CentOS 7 (GLIBCXX_3.4.19)

**Target System Compatibility:**
```
Build on Ubuntu 20.04 → Works on Ubuntu 20.04, 22.04, 24.04, etc.
Build on Ubuntu 24.04 → Only works on Ubuntu 24.04+ (GLIBCXX_3.4.32)
```

**How to implement:**
```bash
# On Ubuntu 20.04 or similar
sudo apt-get install qt5-default build-essential
cd /path/to/generic-cracker/cracker
qmake && make
cd ..
./package.sh
```

The resulting binary will use GLIBCXX_3.4.28 or lower, compatible with most systems.

### Solution 2: Fully Static Build with Static Qt5

Build Qt5 itself as a static library, then link against it.

**Warning:** This is VERY time-consuming (2-4 hours compile time) and produces larger binaries.

**Steps:**

1. **Build static Qt5** (one-time setup):
```bash
wget https://download.qt.io/official_releases/qt/5.15/5.15.2/single/qt-everywhere-src-5.15.2.tar.xz
tar xf qt-everywhere-src-5.15.2.tar.xz
cd qt-everywhere-src-5.15.2

./configure -static -release -prefix /opt/qt5-static \
    -nomake examples -nomake tests \
    -opensource -confirm-license

make -j$(nproc)  # Takes 2-4 hours
sudo make install
```

2. **Build cracker with static Qt5**:
```bash
cd /path/to/generic-cracker/cracker
/opt/qt5-static/bin/qmake CONFIG+=static
make
```

3. **Result**: Single ~15MB binary with NO dependencies (except libc/libm/libpthread)

**Pros:**
- Truly portable
- No GLIBCXX issues
- No library bundling needed

**Cons:**
- 2-4 hour Qt5 compile time
- Larger binary size (~15MB vs 71KB)
- Must rebuild Qt5 on each build machine

### Solution 3: Docker Build Environment

Use Docker to build on a controlled older environment:

```dockerfile
# Dockerfile
FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    qt5-default \
    build-essential \
    p7zip-full

WORKDIR /build
COPY . .

RUN cd cracker && qmake && make && cd .. && ./package.sh

CMD ["bash"]
```

**Build:**
```bash
docker build -t cracker-builder .
docker run -v $(pwd):/output cracker-builder cp generic-cracker.7z /output/
```

### Solution 4: Bundle libstdc++ with Wrapper Script Rename

Modify Hashtopolis configuration to use a wrapper script instead of the binary directly.

**Package Structure:**
```
generic-cracker/
├── cracker              # Wrapper script (sets LD_LIBRARY_PATH)
├── cracker.bin          # Actual binary
└── lib/
    ├── libQt5Core.so.5
    └── libstdc++.so.6   # Bundled from build system
```

**Hashtopolis Configuration:**
Instead of pointing to:
```
/path/to/generic-cracker/cracker.bin
```

Point to:
```
/path/to/generic-cracker/cracker
```

The wrapper script will set `LD_LIBRARY_PATH` and call `cracker.bin`.

**Limitations:**
- Requires Hashtopolis configuration change
- May not work if Hashtopolis hardcodes `.bin` extension

## Current Build Configuration

The [cracker.pro](cracker/cracker.pro) file currently includes:

```qmake
# Static link libstdc++ and libgcc to avoid GLIBCXX version issues
# Use compiler flags to force static linking of these runtime libraries
QMAKE_LFLAGS += -static-libstdc++ -static-libgcc
```

**Status:** These flags have **no effect** because Qt5Core.so is a shared library with dynamic dependencies.

**Recommendation:** Remove these flags and use Solution 1 (build on older system) instead.

## Checking System Compatibility

### On Build System

Check what GLIBCXX version the binary requires:
```bash
objdump -T ./cracker | grep GLIBCXX | sort -V | tail -5
```

Check what's available:
```bash
strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBCXX | sort -V | tail -5
```

### On Target System

Check available GLIBCXX versions:
```bash
strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBCXX | sort -V | tail -10
```

If the target system doesn't have `GLIBCXX_3.4.32` (required by binary built on Ubuntu 24.04), it will fail.

## Summary

| Solution | Difficulty | Build Time | Binary Size | Portability |
|----------|-----------|------------|-------------|-------------|
| Build on older system | Easy | 5 minutes | 71KB | ⭐⭐⭐⭐⭐ |
| Static Qt5 build | Hard | 2-4 hours | 15MB | ⭐⭐⭐⭐⭐ |
| Docker build | Medium | 10 minutes | 71KB | ⭐⭐⭐⭐⭐ |
| Bundle + wrapper | Easy | 5 minutes | 71KB | ⭐⭐⭐ (config dependent) |

**Recommended:** Use Solution 1 (build on Ubuntu 20.04 or older)
