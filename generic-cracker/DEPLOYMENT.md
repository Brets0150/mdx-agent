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
