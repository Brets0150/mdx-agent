#!/bin/bash
################################################################################
# MDX Agent - Portable Python Package Script
# Creates a package that uses system Python (no PyInstaller, no GLIBC issues)
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MDX Agent Portable Python Package${NC}"
echo -e "${GREEN}========================================${NC}"

# Configuration
PACKAGE_NAME="mdx-agent"
BUILD_DIR="$(pwd)"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}"

# Check if Python script exists
if [ ! -f "mdx-agent.py" ]; then
    echo -e "${RED}Error: mdx-agent.py not found${NC}"
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
mkdir -p "$PACKAGE_DIR/mdx_bin"

# Copy Python script
echo -e "${GREEN}Copying Python script...${NC}"
cp mdx-agent.py "$PACKAGE_DIR/mdx-agent.py"
chmod +x "$PACKAGE_DIR/mdx-agent.py"

# Create wrapper script that uses system Python
echo -e "${GREEN}Creating launcher scripts...${NC}"

# Main launcher (mdx-agent)
cat > "$PACKAGE_DIR/mdx-agent" << 'EOF'
#!/bin/bash
# MDX Agent Launcher - Uses system Python3
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/mdx-agent.py" "$@"
EOF
chmod +x "$PACKAGE_DIR/mdx-agent"

# Binary-named launcher (mdx-agent.bin) for compatibility
cat > "$PACKAGE_DIR/mdx-agent.bin" << 'EOF'
#!/bin/bash
# MDX Agent Binary Launcher - Uses system Python3
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/mdx-agent.py" "$@"
EOF
chmod +x "$PACKAGE_DIR/mdx-agent.bin"

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
else
    echo -e "${YELLOW}Warning: README.md not found${NC}"
fi
if [ -f "$BUILD_DIR/LICENSE" ]; then
    cp "$BUILD_DIR/LICENSE" "$PACKAGE_DIR/"
fi

# Create version info file
echo -e "${GREEN}Creating version info...${NC}"
cat > "$PACKAGE_DIR/VERSION" << EOF
MDX Agent v3.0 (Portable Python)
MDXfind Wrapper for Hashtopolis
Built: $(date)
System: $(uname -s) $(uname -m)
Build Method: Portable Python (no compilation)
Python Version Required: 3.6+
Package Type: Source Distribution
EOF

# Show package contents
echo -e "${GREEN}Package contents:${NC}"
ls -lh "$PACKAGE_DIR" | grep -v "^total" | head -20

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
    RATIO=$(echo "scale=1; (1 - $COMPRESSED / $UNCOMPRESSED) * 100" | bc 2>/dev/null || echo "N/A")
    if [ "$RATIO" != "N/A" ]; then
        echo -e "${GREEN}Compression: ${UNCOMPRESSED} → ${COMPRESSED} bytes (${RATIO}% reduction)${NC}"
    fi
else
    echo -e "${YELLOW}Warning: 7z not found. Install p7zip-full to create archive${NC}"
    echo -e "${YELLOW}Package directory created at: ${PACKAGE_DIR}${NC}"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Packaging complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Package directory: ${GREEN}${PACKAGE_DIR}${NC}"
if [ -f "${PACKAGE_NAME}.7z" ]; then
    echo -e "Archive file: ${GREEN}${PACKAGE_NAME}.7z (${ARCHIVE_SIZE})${NC}"
fi
echo ""
echo -e "To test the package:"
echo -e "  ${YELLOW}cd ${PACKAGE_DIR}${NC}"
echo -e "  ${YELLOW}./mdx-agent --help${NC}"
echo -e "  ${YELLOW}./mdx-agent keyspace -w /path/to/wordlist.txt${NC}"
echo ""
echo -e "To deploy:"
echo -e "  1. Copy ${GREEN}${PACKAGE_NAME}.7z${NC} to target system"
echo -e "  2. Extract: ${YELLOW}7z x ${PACKAGE_NAME}.7z${NC}"
echo -e "  3. Run: ${YELLOW}./${PACKAGE_NAME}/mdx-agent crack -a hashes.txt -w wordlist.txt${NC}"
echo ""
echo -e "${GREEN}Note:${NC} Target system only needs Python 3.6+ (standard on all modern Linux)"
echo -e "${GREEN}Documentation:${NC} See README.md in the package for full details"
