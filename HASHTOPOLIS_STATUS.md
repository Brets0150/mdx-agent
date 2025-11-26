# Hashtopolis Status Reporting Requirements

## Analysis of Agent Expectations

Based on the Hashtopolis agent code in `agent-python/htpclient/generic_cracker.py` and `generic_status.py`:

### Required Output Format

The cracker must output periodic status lines in this format:
```
STATUS <progress> <speed>
```

Where:
- **progress**: Integer from 0 to 10000 (representing 0.00% to 100.00%)
- **speed**: Integer representing hashes/passwords tested per second

### Cracked Hash Format

Lines containing `:` are parsed as cracked hashes:
```
hash:plaintext:algorithm
```

### Agent Behavior

1. **During Cracking** (`run_chunk`):
   - Agent monitors stdout for STATUS lines
   - Parses progress and speed from STATUS lines
   - Sends updates to Hashtopolis server with progress
   - Collects cracked hashes (lines with `:`) and sends them in batches

2. **Benchmark** (`run_benchmark`):
   - Runs with `--timeout=<seconds>`
   - Expects at least one STATUS line in output
   - Uses the last valid STATUS line's progress to calculate benchmark speed
   - Formula: `speed = progress / 10000` (as a fraction of completion)
   - **ERROR if no valid STATUS**: "Generic benchmark failed!"

3. **Keyspace** (`measure_keyspace`):
   - Runs `keyspace` command
   - Expects a single integer as output (total passwords to test)

### Current Problem

MDXfind does NOT output progress information while running. It only outputs:
- Initial diagnostic messages
- Cracked hashes (in format `plaintext:hash:algorithm`)
- No progress updates

Our current cracker outputs only:
```
STATUS 10000 <count>
```
At the very end, which causes:
- No progress updates during cracking (agent thinks it's hung)
- Benchmark fails (because `progress / 10000 = 1.0` always)

### Solution Requirements

We need to:

1. **Calculate Total Keyspace**:
   - Use `-l` parameter (length) if provided
   - Otherwise count wordlist lines
   - Account for `-s` (skip) parameter

2. **Estimate Current Progress**:
   - Since MDXfind doesn't tell us position, we need to:
     - Count passwords processed (estimate)
     - Use time-based estimation
     - Monitor MDXfind output for any positional hints

3. **Calculate Speed**:
   - Track passwords processed over time
   - Update periodically (every 1-5 seconds)

4. **Output STATUS Lines Periodically**:
   - Every 1-5 seconds during operation
   - Format: `STATUS <progress_int> <speed_int>`
   - Example: `STATUS 2500 15000` (25.00% complete, 15K H/s)

5. **Final STATUS Line**:
   - Output `STATUS 10000 <final_count>` when complete
   - This indicates 100% completion

### Implementation Approach

**Option 1: Time-Based Estimation**
- Calculate expected runtime based on keyspace and estimated speed
- Update progress based on elapsed time
- **Pros**: Simple, no file system monitoring
- **Cons**: Inaccurate if speed varies

**Option 2: Separate Progress Monitor**
- Run MDXfind in background
- Periodically sample its progress (via timing or output)
- Output STATUS lines from wrapper
- **Pros**: More accurate
- **Cons**: More complex

**Option 3: Process Password List in Chunks**
- Split wordlist into smaller chunks
- Process each chunk separately
- Update progress after each chunk
- **Pros**: Accurate progress
- **Cons**: Overhead of multiple MDXfind calls

### Recommended Implementation

Use **Option 2** with threading:

```python
import threading
import time

class ProgressTracker:
    def __init__(self, total_keyspace, skip=0):
        self.total = total_keyspace
        self.skip = skip
        self.start_time = time.time()
        self.processed = 0
        self.cracked = 0

    def estimate_progress(self):
        # Time-based estimation
        elapsed = time.time() - self.start_time
        # Estimate based on elapsed time and total keyspace
        # This is a rough estimate until we have better data
        return min(10000, int((elapsed / estimated_total_time) * 10000))

    def calculate_speed(self):
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            return int(self.processed / elapsed)
        return 0

    def output_status(self):
        progress = self.estimate_progress()
        speed = self.calculate_speed()
        print(f"STATUS {progress} {speed}", flush=True)
```

### Testing Checklist

- [ ] Keyspace command outputs single integer
- [ ] STATUS lines appear periodically during cracking
- [ ] STATUS format is: `STATUS <int> <int>`
- [ ] Progress goes from 0 to 10000
- [ ] Final STATUS line is `STATUS 10000 <count>`
- [ ] Cracked hashes still output correctly
- [ ] Benchmark with `--timeout` produces valid STATUS
- [ ] Agent doesn't report "Invalid benchmark result!"

### Example Expected Output

```
MD5 MD5UC ... [hash type list]
Working on hash types:SALT MD5...
[cracked hashes as they're found]
hash1:plain1:MD5x01
STATUS 1250 12500
hash2:plain2:MD5x01
STATUS 2500 13200
STATUS 3750 13800
hash3:plain3:MD5x01
STATUS 5000 14100
STATUS 6250 14300
STATUS 7500 14200
STATUS 8750 14000
STATUS 10000 3
```

The agent would see:
- Regular progress updates (12.5%, 25%, etc.)
- Speed measurements (~12K-14K H/s)
- 3 cracked hashes
- Final 100% completion
