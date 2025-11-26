# Generic Cracker - Packaging Guide

## Quick Start

To create a portable, self-contained package:

```bash
./package.sh
```

This will create:
- `generic-cracker/` - Portable directory with all dependencies
- `generic-cracker.7z` - Compressed archive (80MB → 19MB)

## What the Package Contains

### Directory Structure
```
generic-cracker/
├── cracker              # Launcher script (USE THIS)
├── cracker.bin          # Main executable
├── lib/                 # Bundled Qt5 and system libraries
│   ├── libQt5Core.so.5
│   ├── libstdc++.so.6
│   ├── libgcc_s.so.1
│   ├── libicui18n.so.74
│   ├── libicuuc.so.74
│   ├── libicudata.so.74
│   ├── libpcre2-16.so.0
│   ├── libpcre2-8.so.0
│   ├── libz.so.1
│   └── libdouble-conversion.so.3
├── mdx_bin/             # MDXfind binaries (all platforms)
│   ├── mdxfind          # Linux x86_64
│   ├── mdxfind.arm6     # ARM variants
│   ├── mdxfind.mac      # macOS
│   └── ...
├── DEPLOYMENT.md        # User deployment instructions
├── VERSION              # Build information
├── README.md            # Project documentation
└── LICENSE              # License file
```

### Key Features

✅ **Fully Portable** - No system Qt5 installation required
✅ **Self-Contained** - All dependencies bundled in `lib/`
✅ **Launcher Script** - Automatically sets `LD_LIBRARY_PATH`
✅ **Multi-Platform MDXfind** - Binaries for Linux, ARM, macOS, FreeBSD
✅ **Compressed** - 80MB → 19MB with LZMA compression

## Deployment to Hashtopolis

### On Build System

1. Build and package:
   ```bash
   cd cracker
   make
   cd ..
   ./package.sh
   ```

2. Upload `generic-cracker.7z` to your server

### On Hashtopolis Server

1. Extract the archive:
   ```bash
   7z x generic-cracker.7z
   ```

2. Move to crackers directory:
   ```bash
   mv generic-cracker /home/admuser/crackers/10/
   ```

3. Test it works:
   ```bash
   /home/admuser/crackers/10/generic-cracker/cracker --help
   ```

### Configure in Hashtopolis

Binary path: `/home/admuser/crackers/10/generic-cracker/cracker`

The launcher script handles library paths automatically, so no special configuration needed!

## Manual Packaging Steps

If you need to customize the packaging:

### 1. Build the Binary

```bash
cd cracker
qmake cracker.pro
make
```

### 2. Create Package Directory

```bash
mkdir -p generic-cracker/lib
mkdir -p generic-cracker/mdx_bin
```

### 3. Copy Binary

```bash
cp cracker/cracker generic-cracker/cracker.bin
chmod +x generic-cracker/cracker.bin
```

### 4. Bundle Qt5 Libraries

```bash
ldd cracker/cracker | grep libQt5 | awk '{print $3}' | xargs -I {} cp {} generic-cracker/lib/
```

### 5. Bundle System Libraries

```bash
ldd cracker/cracker | grep -E "libstdc\+\+|libgcc_s|libicu|libpcre|libz|libdouble-conversion" | awk '{print $3}' | xargs -I {} cp {} generic-cracker/lib/
```

### 6. Create Launcher Script

```bash
cat > generic-cracker/cracker << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$SCRIPT_DIR/lib:$LD_LIBRARY_PATH"
exec "$SCRIPT_DIR/cracker.bin" "$@"
EOF
chmod +x generic-cracker/cracker
```

### 7. Copy MDXfind Binaries

```bash
cp -r mdx_bin/* generic-cracker/mdx_bin/
chmod +x generic-cracker/mdx_bin/*
```

### 8. Create Archive

```bash
7z a -t7z -m0=lzma -mx=9 generic-cracker.7z generic-cracker
```

## Testing the Package

### Verify Dependencies

```bash
cd generic-cracker
LD_LIBRARY_PATH=./lib ldd ./cracker.bin | grep "not found"
```

Should return nothing if all dependencies are bundled.

### Test Functionality

```bash
./cracker --help
./cracker keyspace -w wordlist.txt
./cracker crack -a hashes.txt -w wordlist.txt -t MD5 -s 0 -l 100
```

### Simulate Clean System

To test portability, unset system library paths:

```bash
env -i HOME=$HOME USER=$USER PATH=/bin:/usr/bin ./cracker --help
```

## Troubleshooting

### "Permission denied"

```bash
chmod +x generic-cracker/cracker
chmod +x generic-cracker/cracker.bin
chmod +x generic-cracker/mdx_bin/*
```

### "libQt5Core.so.5: cannot open shared object file"

Check that:
1. `lib/libQt5Core.so.5` exists in the package
2. The launcher script is being used (not calling `cracker.bin` directly)
3. `LD_LIBRARY_PATH` is set correctly

Debug with:
```bash
LD_LIBRARY_PATH=./lib ldd ./cracker.bin
```

### "mdxfind not found"

The cracker looks for mdxfind in:
1. `../mdx_bin/mdxfind` (relative to binary)
2. `./mdx_bin/mdxfind` (current directory)

Make sure mdx_bin is in the correct location relative to the binary.

## Archive Size Comparison

| Content | Uncompressed | Compressed (7z LZMA) | Ratio |
|---------|--------------|----------------------|-------|
| Cracker binary | 71KB | - | - |
| Qt5 libraries | ~4MB | - | - |
| System libraries | ~40MB | - | - |
| MDXfind binaries | ~36MB | - | - |
| **Total** | **80MB** | **19MB** | **76% reduction** |

## Building Static Binary (Alternative)

For a truly standalone binary without bundled libraries:

```bash
# Build Qt5 statically (one-time setup)
./configure -static -release -prefix /opt/qt5-static -nomake examples -nomake tests
make -j$(nproc)
sudo make install

# Build cracker with static Qt5
cd cracker
/opt/qt5-static/bin/qmake cracker.pro CONFIG+=static
make

# Result: Single ~20MB binary with no dependencies
```

Note: Static builds are larger but require no library bundling.

## CI/CD Integration

Add to `.travis.yml` or GitHub Actions:

```yaml
- name: Build and Package
  run: |
    cd cracker
    qmake cracker.pro
    make
    cd ..
    ./package.sh

- name: Upload Artifact
  uses: actions/upload-artifact@v2
  with:
    name: generic-cracker
    path: generic-cracker.7z
```

## Version Info

The package includes a `VERSION` file with build details:

```
Generic Cracker v1.0
MDXfind Wrapper for Hashtopolis
Built: Tue Nov 26 05:57:16 UTC 2025
System: Linux x86_64
Kernel: 6.8.0-88-generic
```

This helps track which version is deployed on each system.
