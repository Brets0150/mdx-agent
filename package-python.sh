#!/bin/bash
################################################################################
# Generic Cracker - Python Build & Package Script
# Creates a portable, self-contained deployment package
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Generic Cracker Python Packaging${NC}"
echo -e "${GREEN}================================${NC}"

# Configuration
PACKAGE_NAME="generic-cracker"
BUILD_DIR="$(pwd)"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}"

# Check if Python script exists
if [ ! -f "cracker.py" ]; then
    echo -e "${RED}Error: cracker.py not found${NC}"
    exit 1
fi

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${YELLOW}PyInstaller not found. Installing...${NC}"
    pip3 install pyinstaller --break-system-packages
fi

# Clean old build artifacts
echo -e "${GREEN}Cleaning old build artifacts...${NC}"
rm -rf build dist *.spec

# Build executable with PyInstaller
echo -e "${GREEN}Building executable with PyInstaller...${NC}"
pyinstaller --onefile --name cracker cracker.py

# Check if build succeeded
if [ ! -f "dist/cracker" ]; then
    echo -e "${RED}Error: Build failed - executable not found${NC}"
    exit 1
fi

BINARY_SIZE=$(du -h dist/cracker | cut -f1)
echo -e "${GREEN}Executable built successfully: ${BINARY_SIZE}${NC}"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo -e "${YELLOW}Removing old package directory...${NC}"
    rm -rf "$PACKAGE_DIR"
fi

# Create package structure
echo -e "${GREEN}Creating package structure...${NC}"
mkdir -p "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/mdx_bin"

# Copy executable
echo -e "${GREEN}Copying executable...${NC}"
cp dist/cracker "$PACKAGE_DIR/cracker"
chmod +x "$PACKAGE_DIR/cracker"

# Copy MDXfind binaries
echo -e "${GREEN}Copying MDXfind binaries...${NC}"
if [ -d "$BUILD_DIR/mdx_bin" ]; then
    cp -r "$BUILD_DIR/mdx_bin/"* "$PACKAGE_DIR/mdx_bin/"
    chmod +x "$PACKAGE_DIR/mdx_bin/"*
else
    echo -e "${YELLOW}Warning: mdx_bin directory not found${NC}"
fi

# Copy documentation
echo -e "${GREEN}Copying documentation...${NC}"
if [ -f "$BUILD_DIR/README.md" ]; then
    cp "$BUILD_DIR/README.md" "$PACKAGE_DIR/"
fi
if [ -f "$BUILD_DIR/LICENSE" ]; then
    cp "$BUILD_DIR/LICENSE" "$PACKAGE_DIR/"
fi

# Create deployment README
echo -e "${GREEN}Creating deployment instructions...${NC}"
cat > "$PACKAGE_DIR/DEPLOYMENT.md" << 'EOF'
# Generic Cracker - Deployment Instructions (Python Version)

## Quick Start

1. Extract the archive to your desired location
2. Run the cracker directly:
   ```bash
   ./cracker crack -a hashlist.txt -w wordlist.txt -t MD5
   ```

## Directory Structure

- `cracker` - Standalone executable (Python + PyInstaller)
- `mdx_bin/` - MDXfind binaries for different platforms

## Key Advantages of Python Version

✅ **No library dependencies** - Single executable with embedded Python runtime
✅ **No GLIBCXX issues** - Doesn't depend on C++ standard library
✅ **Smaller package** - 7-10MB vs 80MB with Qt5
✅ **More portable** - Works across wide range of Linux distributions
✅ **Easier to maintain** - Python code is simpler and more readable

## Usage

### Calculate Keyspace
```bash
./cracker keyspace -w wordlist.txt
```

### Crack Hashes
```bash
./cracker crack -a hashlist.txt -w wordlist.txt -t MD5 -s 0 -l 100
```

### Available Options

- `-w, --wordlist <file>` - Wordlist for dictionary attack
- `-a, --attacked-hashlist <file>` - File containing hashes to crack
- `-t, --type <types>` - Hash types (e.g., 'MD5', 'ALL,!user,salt')
- `-s, --skip <num>` - Skip first N passwords
- `-l, --length <num>` - Process N passwords
- `-i, --iterations <num>` - Iteration count for hash algorithms
- `--timeout <seconds>` - Maximum runtime

### Output Format

Cracked hashes are output in the format:
```
hash:plaintext:algorithm
```

Example:
```
5f4dcc3b5aa765d61d8327deb882cf99:password:MD5x01
```

## Hashtopolis Integration

This cracker is compatible with Hashtopolis. Simply configure the binary path:
```
/path/to/generic-cracker/cracker
```

The executable is self-contained and requires no wrapper scripts or library paths.

## Troubleshooting

### "Permission denied" error
```bash
chmod +x cracker
./cracker --help
```

### "MDXfind not found" error
Ensure the `mdx_bin/` directory is in the same location as the `cracker` executable.

## System Requirements

- **Linux x86_64**
- **Kernel 3.2.0 or later**
- **No Python installation required** (embedded in executable)
- **No Qt5 required** (pure Python implementation)
- **No C++ libraries required** (no libstdc++ or GLIBCXX dependencies)

## Comparison: Python vs C++ Version

| Feature | Python Version | C++ Version |
|---------|---------------|-------------|
| Executable Size | 7.2MB | 71KB (+80MB libraries) |
| Package Size | 10MB | 80MB → 19MB (7z) |
| Dependencies | None (self-contained) | Qt5, libstdc++, libgcc, etc. |
| GLIBCXX Issues | ✅ None | ❌ Must build on older system |
| Portability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Build Complexity | Simple | Complex |
| Code Size | 320 lines | 1,268 lines |
| Maintenance | Easy | Moderate |

## Notes

- All functionality is identical to the C++ version
- Performance is comparable (MDXfind does the heavy lifting)
- Python runtime is embedded in the executable
- Works on any Linux distribution without additional dependencies
EOF

# Create version info file
echo -e "${GREEN}Creating version info...${NC}"
cat > "$PACKAGE_DIR/VERSION" << EOF
Generic Cracker v2.0 (Python)
MDXfind Wrapper for Hashtopolis
Built: $(date)
System: $(uname -s) $(uname -m)
Kernel: $(uname -r)
Build Method: PyInstaller $(pyinstaller --version 2>&1 | head -1)
Executable Size: ${BINARY_SIZE}
EOF

# Show package contents
echo -e "${GREEN}Package contents:${NC}"
tree -L 2 "$PACKAGE_DIR" 2>/dev/null || find "$PACKAGE_DIR" -maxdepth 2 -type f -o -type d | head -20

# Calculate package size
PACKAGE_SIZE=$(du -sh "$PACKAGE_DIR" | cut -f1)
echo -e "${GREEN}Package size: ${PACKAGE_SIZE}${NC}"

# Create 7z archive
echo -e "${GREEN}Creating 7z archive...${NC}"
if command -v 7z &> /dev/null; then
    # Remove old archive if exists
    [ -f "${PACKAGE_NAME}.7z" ] && rm "${PACKAGE_NAME}.7z"

    # Create compressed archive with maximum compression
    7z a -t7z -m0=lzma -mx=9 "${PACKAGE_NAME}.7z" "${PACKAGE_NAME}"

    ARCHIVE_SIZE=$(du -sh "${PACKAGE_NAME}.7z" | cut -f1)
    echo -e "${GREEN}Archive created: ${PACKAGE_NAME}.7z (${ARCHIVE_SIZE})${NC}"

    # Show compression stats
    UNCOMPRESSED=$(du -sb "${PACKAGE_NAME}" | awk '{print $1}')
    COMPRESSED=$(du -sb "${PACKAGE_NAME}.7z" | awk '{print $1}')
    RATIO=$(echo "scale=1; (1 - $COMPRESSED / $UNCOMPRESSED) * 100" | bc)
    echo -e "${GREEN}Compression: ${UNCOMPRESSED} → ${COMPRESSED} bytes (${RATIO}% reduction)${NC}"
else
    echo -e "${YELLOW}Warning: 7z not found. Install p7zip-full to create archive${NC}"
    echo -e "${YELLOW}Package directory created at: ${PACKAGE_DIR}${NC}"
fi

# Show dependencies info
echo -e "${GREEN}Checking dependencies...${NC}"
echo -e "${YELLOW}Executable dependencies:${NC}"
ldd "$PACKAGE_DIR/cracker" | head -10

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Packaging complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "Package directory: ${GREEN}${PACKAGE_DIR}${NC}"
if [ -f "${PACKAGE_NAME}.7z" ]; then
    echo -e "Archive file: ${GREEN}${PACKAGE_NAME}.7z (${ARCHIVE_SIZE})${NC}"
fi
echo ""
echo -e "${GREEN}✅ Key Advantages:${NC}"
echo -e "  • No Qt5 dependencies"
echo -e "  • No libstdc++ / GLIBCXX issues"
echo -e "  • Single self-contained executable"
echo -e "  • Portable across Linux distributions"
echo ""
echo -e "To test the package:"
echo -e "  ${YELLOW}cd ${PACKAGE_DIR}${NC}"
echo -e "  ${YELLOW}./cracker --help${NC}"
echo -e "  ${YELLOW}./cracker keyspace -w /path/to/wordlist.txt${NC}"
echo ""
echo -e "To deploy:"
echo -e "  1. Copy ${GREEN}${PACKAGE_NAME}.7z${NC} to target system"
echo -e "  2. Extract: ${YELLOW}7z x ${PACKAGE_NAME}.7z${NC}"
echo -e "  3. Run: ${YELLOW}./${PACKAGE_NAME}/cracker crack -a hashes.txt -w wordlist.txt${NC}"
