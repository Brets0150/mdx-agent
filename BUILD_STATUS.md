# Generic Cracker - Build Status and Next Steps

## Current Status

### ✅ Completed
1. **Core Functionality** - Cracker successfully cracks hashes using MDXfind
2. **Bug Fixes** - Fixed 3 critical bugs preventing hash output:
   - Invalid `-g` option consuming wordlist parameter
   - Missing salt file parameter for MDXfind
   - Premature process termination
3. **Hashtopolis Compatibility** - Modified to:
   - Silently ignore unknown parameters from Hashtopolis
   - Renamed `--hash-type` to `-t`/`--type` to avoid conflicts
4. **Portable Packaging** - Created `package.sh` script that bundles all Qt5 dependencies

### ⚠️ Outstanding Issue: GLIBCXX Version Compatibility

**Problem:**
```
/lib/x86_64-linux-gnu/libstdc++.so.6: version `GLIBCXX_3.4.32' not found
```

**Current Build System:**
- Ubuntu 24.04 (WSL)
- GLIBCXX versions available: up to 3.4.33
- Binary requires: GLIBCXX_3.4.32

**Target System (Hashtopolis):**
- Has older libstdc++ without GLIBCXX_3.4.32
- Maximum GLIBCXX version: Unknown (likely 3.4.28 or 3.4.29)

## Why Static Linking Doesn't Work

Multiple attempts were made to statically link libstdc++:

### Attempt 1: `-Wl,-Bstatic -lstdc++`
```qmake
QMAKE_LFLAGS += -Wl,-Bstatic -lstdc++ -lgcc -Wl,-Bdynamic
```
**Result:** FAILED - Libraries still dynamically linked

### Attempt 2: Direct Static Library Paths
```qmake
LIBS += /usr/lib/gcc/x86_64-linux-gnu/13/libstdc++.a
LIBS += /usr/lib/gcc/x86_64-linux-gnu/13/libgcc.a
```
**Result:** FAILED - Libraries still dynamically linked

### Attempt 3: `-static-libstdc++ -static-libgcc`
```qmake
QMAKE_LFLAGS += -static-libstdc++ -static-libgcc
```
**Result:** FAILED - Libraries still dynamically linked

### Root Cause Analysis

The cracker binary depends on **Qt5Core.so**, which is a **shared library**:

```bash
$ ldd /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 | grep libstdc
libstdc++.so.6 => /lib/x86_64-linux-gnu/libstdc++.so.6
```

When we link against Qt5Core.so:
1. Qt5Core.so brings its own dynamic dependency on libstdc++
2. The dynamic linker resolves this at runtime
3. Our static linking flags are **overridden** by Qt5Core's dependencies

**Analogy:** It's like trying to make a house waterproof while one of the pre-built walls has holes in it. We can waterproof our own construction, but the dependency (Qt5Core) has its own requirements that we can't control.

## Solutions

See [GLIBCXX_SOLUTION.md](GLIBCXX_SOLUTION.md) for detailed analysis of all solutions.

### Recommended Solution: Build on Ubuntu 20.04

The best approach is to build the cracker on **Ubuntu 20.04 LTS** which has:
- GLIBCXX_3.4.28 (compatible with most systems)
- Qt5 5.12.8 (stable and well-tested)
- Wide compatibility with target systems

**Why this works:**
- Binaries built on older systems work on newer systems (forward compatibility)
- Ubuntu 20.04 is still widely supported (LTS until 2025)
- Most production systems have at least GLIBCXX_3.4.28

**How to implement:**

#### Option 1: WSL Ubuntu 20.04 (Recommended)
```bash
# Install Ubuntu 20.04 in WSL
wsl --install -d Ubuntu-20.04

# Launch Ubuntu 20.04
wsl -d Ubuntu-20.04

# Inside Ubuntu 20.04 WSL:
sudo apt-get update
sudo apt-get install qt5-default build-essential p7zip-full

# Build
cd /mnt/u/Work/C-Projects/generic-cracker
cd cracker
qmake && make
cd ..
./package.sh
```

#### Option 2: Docker Build
```bash
# Use Docker to build in Ubuntu 20.04 environment
docker run -it -v $(pwd):/build ubuntu:20.04 bash

# Inside container:
apt-get update
apt-get install -y qt5-default build-essential p7zip-full
cd /build/cracker
qmake && make
cd ..
./package.sh
```

#### Option 3: VM or Physical Ubuntu 20.04 System
- Install Ubuntu 20.04 LTS in VirtualBox/VMware
- Build on that system
- Transfer the resulting `generic-cracker.7z` package

### Alternative Solution: Fully Static Qt5 Build

Build Qt5 itself as a static library (2-4 hours compile time):

See [GLIBCXX_SOLUTION.md](GLIBCXX_SOLUTION.md) for complete instructions.

**Pros:**
- Truly portable binary
- No GLIBCXX issues
- Works on any Linux system

**Cons:**
- Very long compile time (2-4 hours)
- Larger binary size (~15MB vs 71KB)
- Must rebuild Qt5 on each build machine

## Current Binary Information

**Build Environment:**
- System: WSL Ubuntu 24.04
- Kernel: 6.8.0-88-generic
- GCC: 13.x
- GLIBCXX: 3.4.32 (requires this version at minimum)

**Binary Details:**
```bash
$ file cracker
cracker: ELF 64-bit LSB executable, x86-64, dynamically linked

$ ldd cracker | grep libstdc
libstdc++.so.6 => /lib/x86_64-linux-gnu/libstdc++.so.6

$ ls -lh cracker
-rwxrwxrwx 1 seawolf seawolf 1.8M Nov 26 06:44 cracker
```

## Testing on Target System

To verify compatibility on the target Hashtopolis system:

```bash
# Check available GLIBCXX versions
strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBCXX | sort -V

# Should include at least GLIBCXX_3.4.32 for current binary to work
```

## Files Modified

### Core Functionality
- [cracker/runthread.cpp](cracker/runthread.cpp) - Fixed MDXfind integration bugs
- [cracker/main.cpp](cracker/main.cpp) - Added Hashtopolis compatibility

### Build System
- [cracker/cracker.pro](cracker/cracker.pro) - Added static linking attempts (ineffective)
- [package.sh](package.sh) - Portable packaging script

### Documentation
- [GLIBCXX_SOLUTION.md](GLIBCXX_SOLUTION.md) - Complete analysis and solutions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Updated with GLIBCXX info
- [BUILD.md](BUILD.md) - Build instructions
- [PACKAGING.md](PACKAGING.md) - Packaging guide

## Next Steps

1. **Choose build environment:**
   - ⭐ **Recommended:** WSL Ubuntu 20.04
   - Alternative: Docker with Ubuntu 20.04
   - Alternative: Static Qt5 build (if portability critical)

2. **Rebuild on older environment:**
   ```bash
   cd cracker
   qmake && make
   cd ..
   ./package.sh
   ```

3. **Test on target system:**
   ```bash
   ./cracker --help
   ./cracker crack -a hashes.txt -w wordlist.txt -t MD5
   ```

4. **Deploy to Hashtopolis:**
   - Extract `generic-cracker.7z`
   - Configure binary path in Hashtopolis
   - Run test task

## Quick Reference

| File | Purpose |
|------|---------|
| [cracker/cracker](cracker/cracker) | Main binary (dynamically linked) |
| [package.sh](package.sh) | Create portable package |
| [generic-cracker/cracker](generic-cracker/cracker) | Launcher script (sets LD_LIBRARY_PATH) |
| [generic-cracker/cracker.bin](generic-cracker/cracker.bin) | Binary in package |
| [GLIBCXX_SOLUTION.md](GLIBCXX_SOLUTION.md) | Detailed GLIBCXX analysis |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and fixes |

## Contact & Support

For issues related to:
- **MDXfind integration:** Check [runthread.cpp](cracker/runthread.cpp) implementation
- **Hashtopolis compatibility:** Check [main.cpp](cracker/main.cpp) parameter handling
- **GLIBCXX errors:** See [GLIBCXX_SOLUTION.md](GLIBCXX_SOLUTION.md)
- **Packaging:** See [PACKAGING.md](PACKAGING.md)
