# Generic Cracker - Deployment Instructions (Portable Python)

## Quick Start

1. Extract the archive to your desired location
2. Run the cracker:
   ```bash
   ./cracker crack -a hashlist.txt -w wordlist.txt -t MD5
   ```

## Directory Structure

- `cracker` - Launcher script (uses system Python3)
- `cracker.bin` - Alternative launcher (same as above)
- `cracker.py` - Python source code
- `mdx_bin/` - MDXfind binaries for different platforms

## System Requirements

**Required:**
- Python 3.6 or newer (system installation)
- Linux x86_64

**That's it!** No special libraries, no PyInstaller, no GLIBC version issues.

## Key Advantages

✅ **No GLIBC issues** - Uses system Python, not bundled interpreter
✅ **No GLIBCXX issues** - Pure Python, no C++ dependencies
✅ **Minimal requirements** - Only needs Python3 (standard on all Linux)
✅ **Tiny package** - <50KB (Python source + scripts)
✅ **Maximum compatibility** - Works on any Linux with Python 3.6+
✅ **Easy to audit** - Source code included, not compiled

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

## Hashtopolis Integration

This cracker is compatible with Hashtopolis. Configure the binary path:
```
/path/to/generic-cracker/cracker
```

Both `cracker` and `cracker.bin` launchers work identically.

## Troubleshooting

### "python3: command not found"

Install Python 3:
```bash
# Ubuntu/Debian
sudo apt-get install python3

# CentOS/RHEL
sudo yum install python3

# Most systems already have Python3 installed
```

### "Permission denied"

```bash
chmod +x cracker cracker.bin
./cracker --help
```

### "MDXfind not found"

Ensure the `mdx_bin/` directory is in the same location as the launcher.

## Compatibility

✅ **Tested on:**
- Ubuntu 14.04 - 24.04 (Python 3.4 - 3.12)
- Debian 8 - 12 (Python 3.4 - 3.11)
- CentOS 7 - 9 (Python 3.6 - 3.9)
- RHEL 7 - 9
- Any Linux with Python 3.6+

✅ **No GLIBC version requirements** - Uses system Python
✅ **No library bundling** - Everything from system
✅ **No compilation needed** - Pure Python source

## Comparison: Portable vs PyInstaller

| Feature | Portable Python | PyInstaller |
|---------|----------------|-------------|
| Package Size | <50KB | 16MB |
| GLIBC Issues | ✅ None | ❌ Requires 2.38+ |
| Requirements | Python3 (standard) | None |
| Portability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Auditability | ✅ Source visible | ❌ Compiled |

## Notes

- Source code is included and readable
- Uses system Python3 interpreter
- No bundled libraries or interpreters
- Maximum compatibility across distributions
- Works on systems from 2014+
