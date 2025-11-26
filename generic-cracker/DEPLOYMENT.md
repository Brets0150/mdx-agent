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
