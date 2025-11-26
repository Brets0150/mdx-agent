#!/bin/bash
################################################################################
# Generic Cracker - Bundle & Package Script
# Creates a portable, self-contained deployment package
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Generic Cracker Packaging Script${NC}"
echo -e "${GREEN}================================${NC}"

# Configuration
PACKAGE_NAME="generic-cracker"
BUILD_DIR="$(pwd)"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}"
CRACKER_BIN="${BUILD_DIR}/cracker/cracker"

# Check if binary exists
if [ ! -f "$CRACKER_BIN" ]; then
    echo -e "${RED}Error: Cracker binary not found at $CRACKER_BIN${NC}"
    echo -e "${YELLOW}Run 'make' in the cracker directory first${NC}"
    exit 1
fi

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo -e "${YELLOW}Removing old package directory...${NC}"
    rm -rf "$PACKAGE_DIR"
fi

# Create package structure
echo -e "${GREEN}Creating package structure...${NC}"
mkdir -p "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/lib"
mkdir -p "$PACKAGE_DIR/mdx_bin"

# Copy main binary and rename
echo -e "${GREEN}Copying cracker binary...${NC}"
cp "$CRACKER_BIN" "$PACKAGE_DIR/cracker.bin"
chmod +x "$PACKAGE_DIR/cracker.bin"

# Copy MDXfind binaries
echo -e "${GREEN}Copying MDXfind binaries...${NC}"
if [ -d "$BUILD_DIR/mdx_bin" ]; then
    cp -r "$BUILD_DIR/mdx_bin/"* "$PACKAGE_DIR/mdx_bin/"
    chmod +x "$PACKAGE_DIR/mdx_bin/"*
else
    echo -e "${YELLOW}Warning: mdx_bin directory not found${NC}"
fi

# Find and copy Qt5 dependencies
echo -e "${GREEN}Bundling Qt5 libraries...${NC}"
QT_LIBS=$(ldd "$CRACKER_BIN" | grep libQt5 | awk '{print $3}')
if [ -z "$QT_LIBS" ]; then
    echo -e "${YELLOW}Warning: No Qt5 libraries found in ldd output${NC}"
else
    for lib in $QT_LIBS; do
        if [ -f "$lib" ]; then
            echo "  Copying $(basename $lib)"
            cp "$lib" "$PACKAGE_DIR/lib/"
        fi
    done
fi

# Copy essential system libraries (libstdc++, libgcc)
echo -e "${GREEN}Bundling system libraries...${NC}"
SYS_LIBS=$(ldd "$CRACKER_BIN" | grep -E "libstdc\+\+|libgcc_s|libicui18n|libicuuc|libicudata|libpcre|libz\.so|libdouble-conversion" | awk '{print $3}')
for lib in $SYS_LIBS; do
    if [ -f "$lib" ]; then
        echo "  Copying $(basename $lib)"
        cp "$lib" "$PACKAGE_DIR/lib/"
    fi
done

# Create launcher wrapper script
echo -e "${GREEN}Creating launcher script...${NC}"
cat > "$PACKAGE_DIR/cracker" << 'EOF'
#!/bin/bash
################################################################################
# Generic Cracker Launcher
# Sets up library paths and executes the cracker binary
################################################################################

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set library path to include bundled libraries
export LD_LIBRARY_PATH="$SCRIPT_DIR/lib:$LD_LIBRARY_PATH"

# Execute the cracker binary with all arguments passed through
exec "$SCRIPT_DIR/cracker.bin" "$@"
EOF

chmod +x "$PACKAGE_DIR/cracker"

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
# Generic Cracker - Deployment Instructions

## Quick Start

1. Extract the archive to your desired location
2. Run the cracker using the launcher script:
   ```bash
   ./cracker crack -a hashlist.txt -w wordlist.txt -t MD5
   ```

## Directory Structure

- `cracker` - Launcher script (use this to run the cracker)
- `cracker.bin` - Main executable binary
- `lib/` - Bundled Qt5 and system libraries
- `mdx_bin/` - MDXfind binaries for different platforms

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

This cracker is compatible with Hashtopolis. The launcher script ensures
all required libraries are available without system installation.

## Troubleshooting

### "Permission denied" error
```bash
chmod +x cracker
./cracker --help
```

### "cannot open shared object file" error
The launcher script should handle this automatically. If you still see this error:
1. Verify all files in `lib/` directory are present
2. Check that `cracker.bin` has execute permissions
3. Try running directly: `LD_LIBRARY_PATH=./lib ./cracker.bin --help`

## System Requirements

- Linux x86_64
- Kernel 3.2.0 or later
- No root access required
- No system-wide Qt5 installation needed

## Notes

- All dependencies are bundled in the `lib/` directory
- The cracker uses MDXfind for hash identification and cracking
- Multiple hash algorithms are supported via MDXfind
EOF

# Create version info file
echo -e "${GREEN}Creating version info...${NC}"
cat > "$PACKAGE_DIR/VERSION" << EOF
Generic Cracker v1.0
MDXfind Wrapper for Hashtopolis
Built: $(date)
System: $(uname -s) $(uname -m)
Kernel: $(uname -r)
EOF

# Show package contents
echo -e "${GREEN}Package contents:${NC}"
tree -L 2 "$PACKAGE_DIR" 2>/dev/null || find "$PACKAGE_DIR" -type f -o -type d

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
    echo -e "${GREEN}Compression ratio: $(du -sb ${PACKAGE_NAME} | awk '{print $1}') -> $(du -sb ${PACKAGE_NAME}.7z | awk '{print $1}') bytes${NC}"
else
    echo -e "${YELLOW}Warning: 7z not found. Install p7zip-full to create archive${NC}"
    echo -e "${YELLOW}Package directory created at: ${PACKAGE_DIR}${NC}"
fi

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Packaging complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "Package directory: ${GREEN}${PACKAGE_DIR}${NC}"
if [ -f "${PACKAGE_NAME}.7z" ]; then
    echo -e "Archive file: ${GREEN}${PACKAGE_NAME}.7z${NC}"
fi
echo ""
echo -e "To test the package:"
echo -e "  ${YELLOW}cd ${PACKAGE_DIR}${NC}"
echo -e "  ${YELLOW}./cracker --help${NC}"
echo ""
echo -e "To deploy:"
echo -e "  1. Copy ${GREEN}${PACKAGE_NAME}.7z${NC} to target system"
echo -e "  2. Extract: ${YELLOW}7z x ${PACKAGE_NAME}.7z${NC}"
echo -e "  3. Run: ${YELLOW}./${PACKAGE_NAME}/cracker crack -a hashes.txt -w wordlist.txt${NC}"
