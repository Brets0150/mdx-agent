# MDX Agent

**Hashtopolis-compatible hash cracking agent powered by MDXfind**

MDX Agent is a lightweight, portable Python wrapper for the MDXfind hash identification and cracking tool, designed for seamless integration with Hashtopolis distributed hash cracking infrastructure.

> **⚠️ CRITICAL HASHTOPOLIS USERS**: Before deploying, read the [Hashtopolis Integration Guide](#hashtopolis-integration-guide) section. Key requirements:
> - **Always use Runtime Benchmark (45+ seconds)**, NOT Speed Benchmark
> - **Tasks cannot be killed** once started—configure small chunk sizes (≤5 minutes)
> - **Output format includes metadata** in plaintext field—requires workflow adjustment
> - Obviously, make it a **CPU-only task**.

## Overview

MDX Agent provides a clean, standards-compliant interface to MDXfind's powerful hash algorithm identification and cracking capabilities. It eliminates C++ library dependencies through a pure Python implementation while maintaining full compatibility with Hashtopolis task management protocols.

### Key Features

- **Universal Hash Support**: Leverages MDXfind's comprehensive algorithm detection
- **Hashtopolis Integration**: Native support for distributed cracking workflows
- **Zero Dependencies**: Pure Python 3.6+ implementation with no external libraries
- **Progress Reporting**: Real-time status updates via MDXfind stderr monitoring

## System Requirements

**Required:**
- Python 3.6 or newer (standard system installation)
- Linux x86_64 (or appropriate platform for included MDXfind binaries)

**That's it!** No special libraries, no PyInstaller, no GLIBC version issues.

### Not Tested on Windows:
I haven’t tested or built this with Windows in mind. There’s likely a straightforward way to implement it in a Windows agent, but I haven’t prioritized that work since none of the systems in my environment run Windows. Given that this is for a hash cracking system, Windows isn’t typically the preferred platform.

### MDXFind Version:
The version of the MDXFind utilities included in this project is the latest available as of November 2025. I happened to be writing this tool at the same time the newest release was published, so this project uses the most up-to-date version as of that date.


## Quick Start

### Installation

**For Hashtopolis Users:**

To use MDX-Agent with Hashtopolis, use the `mdx-agent.7z` archive download URL directly from this project's and add it to Hashtopolis as a generic cracker. No additional setup is required.

**URL:** https://github.com/Brets0150/mdx-agent/raw/refs/heads/master/mdx-agent.7z

![create_bin_version](./docs/create_bin_version.png)

### Then create a new task with the generic binary, which is the MDX-agent.

**NOTE:** When using the `--hash-type` (or -t) option, be sure to enclose the regex expression in double quotes so MDXFIND can correctly identify the hash type. If the double quote is blocked by Hashtopolis, you’ll need to update your server’s "Characters that are not allowed to be used in attack command inputs" configuration to allow it. This ensures the full string is passed to MDXFIND on the command line.

![new-task_mdx-agent](./docs/new-task_mdx-agent.png)

### Lets it run!

![task_running](./docs/task_running.png)
![crack_found](./docs/crack_found.png)

**For Developers/Custom Builds:**

If you wish to modify the MDX-Agent source code:

1. Edit the `mdx-agent.py` file with your changes
2. Run the packaging script to create a new archive:
   ```bash
   ./package-python-portable.sh
   ```
3. The script will generate a new `mdx-agent.7z` archive with your modifications


### Basic Usage

The examples below show command-line usage for standalone testing. When using MDX Agent with Hashtopolis, the `keyspace` and `crack` keywords are automatically added by the Hashtopolis agent—you do not need to specify them manually in your task configuration.

**Calculate wordlist keyspace:**
```bash
./mdx-agent keyspace -w /path/to/wordlist.txt
```

**Crack hashes:**
```bash
./mdx-agent crack \
  -a hashlist.txt \
  -w wordlist.txt \
  -t "ALL,!user,salt" \
  -s 0 \
  -l 10000
```

## Hashtopolis Integration Guide

### Critical Configuration Requirements

#### 1. Benchmark Configuration

**⚠️ IMPORTANT: Always use Runtime Benchmark, NOT Speed Benchmark**

MDX Agent has compatibility issues with Hashtopolis Speed Benchmarks due to the way cracking speed is reported. To avoid benchmark failures:

- **Use Runtime Benchmark only** when creating Hashtopolis tasks
- **Set benchmark runtime to at least 45 seconds in Hashtopolis Server config.**
- Minimum 30 seconds may work, but 45+ seconds ensures MDXfind has sufficient time to start reporting cracking speed. If you have a large hashlist, then you will need to set the benchmark time to 100 seconds.
- This allows Hashtopolis to properly calculate chunk sizes for agent distribution

#### 2. Task Termination Limitations

**⚠️ WARNING: Tasks Cannot Be Killed Once Started**

Due to limitations in the Hashtopolis Python agent's generic mdx-agent implementation ([specifically, lack of error handling on line 116 of the agent code](https://github.com/hashtopolis/agent-python/blob/master/htpclient/generic_cracker.py#L116)), MDX Agent tasks **cannot be terminated** once running. The Hashtopolis agent does not send termination signals to the mdx-agent binary.

**Implications:**

- Tasks will run to completion regardless of Hashtopolis state
- Agent must complete the current chunk before stopping
- No graceful abort mechanism exists

**Workaround Strategy:**

Configure small chunk sizes to minimize impact:

```
Chunk Size: 5 minutes(300 seconds) worth of candidates
```

With 5-minute chunks, an agent will finish and stop within 5 minutes even if the task is terminated.

**Scenarios Where Tasks Won't Stop:**

1. **Task Archived**: `"Task is archived, no work to do"`
   - Agent continues processing current chunk

2. **Agent Set Inactive**: `"Agent is marked inactive!"`
   - Agent continues processing current chunk

3. **Task Deleted**: `"Invalid chunk id 171972"`
   - Agent continues processing current chunk

**Solution:** Only way to stop is to restart the Hashtopolis Python agent process. Plan chunk sizes accordingly.

#### 3. Output Format Caveat

**⚠️ Known Limitation: Non-Standard Plaintext Format**

MDX Agent outputs hash cracking results in a format that **merges algorithm identification, salt, and plaintext** into the plaintext field. This is necessary because Hashtopolis only accepts two values: hash and plaintext.

**Output Format:**
```
hash:algorithm,salt,plaintext
```

**Example:**
```
5f4dcc3b5aa765d61d8327deb882cf99:MD5x01,,password
```

**Problem:**

Hashtopolis stores this as:
- Hash: `5f4dcc3b5aa765d61d8327deb882cf99`
- Plaintext: `MD5x01,,password` ← **Incorrect plaintext**

This "plaintext" includes algorithm metadata and is not the actual password alone.

**Recommended Workflow:**

1. **Initial Import**: Import hash list into Hashtopolis
2. **Run MDX Agent**: Execute MDXfind task to identify algorithm types
3. **Parse Results**: Extract algorithm information from the merged plaintext field
4. **Re-Import**: Import the same hash list again with the correct hash type discovered by MDXfind
5. **Crack Normally**: Run standard cracking tasks with proper algorithm

**Example Workflow:**

```bash
# Step 1: Import unknown hashes
# Hashtopolis: Create hash list "mystery_hashes" hashtypeID "0".

# Step 2: Run MDXfind via Hashtopolis
# Task: MDX Agent
# Result: Discover hashes are "SHA256" from output

# Step 3: Parse MDXfind output
# Extract algorithm from: "hash:SHA256,,plaintext"

# Step 4: Re-import with correct type
# Hashtopolis: Import as SHA256 hash list

# Step 5: Crack with hashcat/proper tool
# Task: Hashcat SHA256 attack
```

**Trade-off:**

While this format requires additional processing, the speed gains from:
- Automated MDXfind execution via Hashtopolis
- Distributed processing across multiple agents
- Elimination of manual terminal monitoring

...far outweigh the workflow adjustment needed.

## Command Reference

### Actions

- `keyspace` - Calculate total candidates in a wordlist
- `crack` - Perform hash cracking attack

### Core Arguments

| Argument | Description |
|----------|-------------|
| `-a`, `--hashlist <file>` | Required: File containing hashes to crack (tab-separated: `hash<TAB>salt`) |
| `-w`, `--wordlist <file>` | Required: Wordlist for dictionary attack |
| `-t`, `--hash-type <types>` | Required: Hash types for MDXfind (default: `ALL,!user,salt`) |
| `-s`, `--skip <num>` | Skip first N passwords in wordlist (for chunking) |
| `-l`, `--limit <num>` | Process only N passwords from wordlist (for chunking) |
| `--timeout <seconds>` | Maximum runtime before termination |
| `--debug` | Enable debug output showing MDXfind stderr and progress tracking |

### Hash Type Examples

- `MD5` - MD5 only
- `SHA1,SHA256` - Multiple specific algorithms
- `ALL,!user,salt` - All algorithms except those requiring username, include salted
- `MD5,SHA*` - MD5 and all SHA variants

See the MDXFind wiki/manual for a full list hash types.

### Output Format

Cracked hashes are output to stdout in Hashtopolis-compatible format:
```
hash:algorithm,plaintext
```

Progress updates are output as:
```
STATUS <progress> <speed>
```

Where `progress` is 0-10000 (representing 0.00% to 100.00%) and `speed` is in hashes/second.

## Architecture

### Signal Handling

MDX Agent includes proper signal handling capabilities for graceful termination:

- **SIGTERM/SIGINT**: Gracefully terminates MDXfind subprocess and exits cleanly
- **Parent Process Death**: Detects orphaned state and shuts down
- **Progress Preservation**: Final STATUS report before shutdown

**Important Note on Hashtopolis Integration:**

While MDX Agent is fully capable of receiving and handling termination signals from Hashtopolis, this functionality is currently not leveraged by the Hashtopolis Python agent. Specifically, the `generic_cracker.py` file in the Hashtopolis agent does not implement error handling or child process termination signals.

If the Hashtopolis agent is updated in the future to include proper error handling and child process termination capabilities, MDX Agent is already prepared to receive and respond to these signals. This signal handling code exists within MDX Agent but remains unused by the current Hashtopolis agent implementation.

### Progress Tracking

Real-time progress is calculated from MDXfind's stderr output:

```
Working on hashmob.net w=248, line 360, Found=0, 12.86Mh/s, 2.76Kc/s
```

The agent parses:
- Current line number in wordlist
- Number of hashes found
- Hash rate (h/s) - reported to Hashtopolis as speed
- Candidate rate (c/s)

Progress updates are sent to stdout every 5 seconds.

### Hash List Format

MDX Agent expects tab-separated hash files compatible with Hashtopolis:

```
hash1<TAB>salt1
hash2<TAB>salt2
hash3<TAB>
```

- First column: Hash value (required)
- Second column: Salt value (optional, empty if unsalted)

**Hashtopolis Integration:**

When using MDX Agent with Hashtopolis, the hash list formatting is handled automatically by Hashtopolis' Hashlist Management API. You do not need to manually separate hashes and salts—simply provide your hash list to Hashtopolis.

MDX Agent will automatically:
- Detect whether the hash list contains salted or unsalted hashes
- Create the appropriate file format for MDXfind
- Generate the correct command-line arguments

This tab-separated format requirement is directly correlated to Hashtopolis' Hashlist Management API structure. Whether your original hash list contains salted or unsalted hashes, MDX Agent processes them correctly without manual intervention.

## Advanced Usage

### Chunked Processing

For distributed cracking, use skip/limit to process wordlist chunks. Hashtopolis will handle all of this for you and add in these command line options automatically.

```bash
# Process chunk 1: lines 0-10000
./mdx-agent crack -a hashes.txt -w wordlist.txt -s 0 -l 10000

# Process chunk 2: lines 10000-20000
./mdx-agent crack -a hashes.txt -w wordlist.txt -s 10000 -l 10000
```

### MDXfind Pass-Through Arguments

Any command-line arguments that MDX Agent does not recognize are automatically passed through to MDXfind for processing. This allows you to leverage MDXfind's full feature set without requiring MDX Agent to explicitly support every MDXfind option.

If an argument is not defined in MDX Agent's command-line interface, it will be forwarded directly to the MDXfind command that is launched:

```bash
./mdx-agent crack -a hashes.txt -w wordlist.txt -t "MD5,!salt,!users" -i 10 -q 10
```

In this example, `-i 10 -q 10` would be passed directly to MDXfind since MDX Agent does not have a handler for it.

### Timeout-Based Tasks

Limit execution time for benchmarking or time-based tasks:

```bash
./mdx-agent crack -a hashes.txt -w wordlist.txt --timeout 3600
```

## Troubleshooting

### "python3: command not found"

Install Python 3 using your system package manager:

```bash
# Ubuntu/Debian
sudo apt-get install python3

# CentOS/RHEL
sudo yum install python3

# Fedora
sudo dnf install python3
```

Most modern Linux distributions include Python 3 by default.

### "Permission denied"

Ensure launcher scripts have execute permissions:

```bash
chmod +x mdx-agent mdx-agent.bin
./mdx-agent --help
```

### "MDXfind not found"

Verify the `mdx_bin/` directory exists in the same location as the launcher:

```bash
ls -la mdx_bin/
```

Ensure the correct MDXfind binary for your platform has execute permissions:

```bash
chmod +x mdx_bin/mdxfind
```

### Debug Mode

Enable debug output to troubleshoot MDXfind execution:

```bash
./mdx-agent crack -a hashes.txt -w wordlist.txt --debug
```

This shows MDXfind's stderr output and progress tracking details.


## Development

### Building from Source

The package script creates a portable distribution:

```bash
./package-python-portable.sh
```

This generates:
- `mdx-agent/` directory with all required files
- `mdx-agent.7z` compressed archive


## Why This Project Exists

### The Hash Misidentification Problem

Anyone who has worked with password cracking knows that hash lists are frequently misidentified. You receive a file labeled "MD5 hashes" that turns out to contain SHA1, NTLM, LM, or any number of different algorithms mixed together.

**Before MDX Agent:**

1. Manually download hash list from source.
2. Run MDXfind on a separate system
3. Babysit the terminal to monitor progress
4. Wait for completion (no parallelization)
5. Manually parse results
6. Re-upload to Hashtopolis with correct algorithm

This process was **time-consuming, manual, and single-threaded**.

**With MDX Agent:**

1. Create Hashtopolis task with MDX Agent
2. Distribute across multiple agents automatically
3. Monitor via Hashtopolis web interface
4. Results stream back in real-time
5. Parse algorithm from output
6. Re-import with correct type

This integration provides **massive speed improvements** through distributed processing and automation.

### Why Python? Why Not C++?

This project was originally developed in C using the Hashtopolis generic cracker code and framework. However, persistent dependency issues forced a migration to Python:

**C++ Version Problems:**

- **Qt5 Dependency Hell**: Generic mdx-agent requires Qt5 libraries
- **Library Compatibility**: Works on Ubuntu 20.04, fails on newer distributions
- **Missing Libraries**: Constant issues with missing .so files on modern systems
- **Fleet Management**: Most production systems run newer OS versions

**Python Version Advantages:**

- **Zero Dependencies**: Pure Python 3 standard library
- **System Python**: No library bundling or version conflicts
- **Easy Development**: AI-assisted C-to-Python conversion
- **Portability**: Runs on any Linux with Python 3.6+
- **Maintainability**: Simpler codebase, easier debugging

The Python rewrite eliminated all deployment issues while maintaining full functionality.

# Credits

- **MDXfind**: The powerful hash identification and cracking engine
- **Hashtopolis**: Distributed hash cracking infrastructure
