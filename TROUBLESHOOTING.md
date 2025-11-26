# Generic Cracker - Troubleshooting Guide

## Common Errors and Solutions

### 1. GLIBCXX Version Errors

**Error:**
```
error while loading shared libraries: libstdc++.so.6: version `GLIBCXX_3.4.32' not found
```

**Cause:** The build system had a newer compiler than the target system.

**Solution:** The package intentionally does NOT bundle `libstdc++.so.6` or `libgcc_s.so.1` to avoid this issue. The system's versions are used instead.

**If you still see this error:**
- Ensure you're using the latest package built with `./package.sh`
- Verify `libstdc++.so.6` is NOT in the `lib/` directory
- Check system compatibility: `strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBCXX`

---

### 2. "Permission denied" Errors

**Error:**
```
bash: ./cracker: Permission denied
```

**Solution:**
```bash
chmod +x cracker
chmod +x cracker.bin
chmod +x mdx_bin/*
```

---

### 3. "libQt5Core.so.5: cannot open shared object file"

**Error:**
```
error while loading shared libraries: libQt5Core.so.5: cannot open shared object file
```

**Cause:** Not using the launcher script, or library path not set correctly.

**Solutions:**

**Option 1** (Recommended): Use the launcher script
```bash
./cracker crack -a hashes.txt -w wordlist.txt
```

**Option 2**: Set library path manually
```bash
LD_LIBRARY_PATH=./lib ./cracker.bin crack -a hashes.txt -w wordlist.txt
```

**Option 3**: Check library exists
```bash
ls -la lib/libQt5Core.so.5
```

---

### 4. "MDXfind executable not found"

**Error:**
```
MDXfind executable not found!
```

**Cause:** `mdx_bin` directory is missing or in wrong location.

**Solution:**
Ensure directory structure is intact:
```
generic-cracker/
├── cracker          ← Launcher
├── cracker.bin      ← Binary
├── lib/             ← Qt5 libraries
└── mdx_bin/         ← MDXfind binaries (must be here!)
    └── mdxfind      ← Linux binary
```

**Verify MDXfind exists:**
```bash
ls -la mdx_bin/mdxfind
```

---

### 5. "Unknown option" Errors

**Error:**
```
Unknown option 'xyz'
```

**This should NOT happen** - the cracker silently ignores unknown options for Hashtopolis compatibility.

**If you see this:**
1. Ensure you're using the latest build
2. Check that [main.cpp:63-71](cracker/main.cpp#L63-L71) contains the unknown option handling code
3. Rebuild: `cd cracker && make && cd .. && ./package.sh`

---

### 6. No Hash Output

**Symptom:** Cracker runs but outputs only `STATUS 10000 0` with no cracked hashes.

**Possible Causes:**

**A) Wrong hash type specified**
```bash
# Try with auto-detection
./cracker crack -a hashes.txt -w wordlist.txt -t "ALL,!user,salt"
```

**B) Wordlist doesn't contain passwords**
```bash
# Verify wordlist is readable
cat wordlist.txt | head
```

**C) MDXfind terminated early**
```bash
# Check for errors
./cracker crack -a hashes.txt -w wordlist.txt -t MD5 2>&1 | grep -i error
```

**D) Hash format incorrect**
The wrapper expects:
- Plain hashes: `hash`
- Salted hashes: `hash:salt` or `hash:salt:plaintext`

---

### 7. System Compatibility Issues

**Error:**
```
/lib64/ld-linux-x86-64.so.2: version `GLIBC_2.XX' not found
```

**Cause:** Target system has older glibc than build system.

**Solutions:**

**Option 1**: Build on older system (e.g., Ubuntu 20.04 instead of 24.04)

**Option 2**: Use static linking (see [PACKAGING.md](PACKAGING.md))

**Option 3**: Check glibc version compatibility
```bash
# On build system
ldd --version

# On target system
ldd --version
```

Target should have >= version of build system.

---

### 8. Hashtopolis Integration Issues

**Error in Hashtopolis:**
```
Error during keyspace measurement: Command returned non-zero exit status
```

**Solutions:**

**A) Test cracker manually first**
```bash
./cracker keyspace -w wordlist.txt
./cracker crack -a hashes.txt -w wordlist.txt -t MD5
```

**B) Check Hashtopolis configuration**
- Binary path: `/full/path/to/cracker` (not `cracker.bin`)
- Ensure launcher script has execute permission

**C) Check Hashtopolis agent logs**
```bash
tail -f /var/log/hashtopolis/agent.log
```

---

### 9. Performance Issues

**Symptom:** Cracking is very slow.

**Check:**

**A) MDXfind is actually running**
```bash
ps aux | grep mdxfind
```

**B) CPU utilization**
```bash
top -p $(pgrep mdxfind)
```

**C) Increase iteration count**
```bash
./cracker crack -a hashes.txt -w wordlist.txt -i 100  # Default is 10
```

---

### 10. Archive Extraction Issues

**Error:**
```
Cannot open generic-cracker.7z
```

**Solution:**
```bash
# Install 7zip
sudo apt-get install p7zip-full

# Extract
7z x generic-cracker.7z
```

**Alternative extraction:**
```bash
# Using tar (if repackaged)
tar -xzf generic-cracker.tar.gz
```

---

## Debugging Commands

### Check Dependencies
```bash
cd generic-cracker
LD_LIBRARY_PATH=./lib ldd ./cracker.bin
```

### Verify No Missing Libraries
```bash
LD_LIBRARY_PATH=./lib ldd ./cracker.bin | grep "not found"
# Should return nothing
```

### Test Launcher Script
```bash
bash -x ./cracker --help
# Shows what the launcher script is doing
```

### Check Qt Version
```bash
strings lib/libQt5Core.so.5 | grep "Qt 5"
```

### Verify MDXfind Works
```bash
./mdx_bin/mdxfind -h MD5 hashfile.txt saltfile.txt wordlist.txt
```

### Check File Permissions
```bash
ls -la cracker cracker.bin
# Both should show -rwxr-xr-x
```

---

## System Requirements

### Minimum
- Linux x86_64
- Kernel 3.2.0+
- GLIBC 2.17+ (CentOS 7, Ubuntu 14.04+)
- 100MB disk space

### Recommended
- Ubuntu 20.04 LTS or newer
- Debian 10+ or RHEL 8+
- Multi-core CPU for better MDXfind performance

### Not Required
- ❌ Root/sudo access
- ❌ Qt5 system installation
- ❌ Development tools

---

## Getting Help

### Information to Provide

When reporting issues, include:

1. **Error message** (full text)
2. **System info:**
   ```bash
   uname -a
   ldd --version
   ```
3. **Package info:**
   ```bash
   cat VERSION
   ```
4. **Command used:**
   ```bash
   ./cracker crack -a ... -w ...
   ```
5. **Library check:**
   ```bash
   LD_LIBRARY_PATH=./lib ldd ./cracker.bin | grep -E "not found|Qt5"
   ```

### Known Working Configurations

✅ Ubuntu 20.04, 22.04, 24.04
✅ Debian 10, 11, 12
✅ CentOS 7, 8, 9
✅ Rocky Linux 8, 9
✅ WSL2 (Ubuntu)

### Known Issues

⚠️ Alpine Linux: Not supported (uses musl instead of glibc)
⚠️ Very old systems (pre-2014): May need static build
⚠️ ARM: Use ARM-specific MDXfind binary from `mdx_bin/`

---

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Permission denied | `chmod +x cracker cracker.bin` |
| libQt5Core not found | Use `./cracker` not `./cracker.bin` |
| GLIBCXX error | Update package (libstdc++ should not be bundled) |
| MDXfind not found | Check `mdx_bin/` directory exists |
| No output | Try `-t "ALL,!user,salt"` for hash type |
| Hashtopolis error | Test manually first: `./cracker --help` |
