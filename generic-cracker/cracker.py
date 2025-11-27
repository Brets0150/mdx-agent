#!/usr/bin/env python3
"""
MDXfind Wrapper for Hashtopolis - Hash Algorithm Identification and Cracking
Python rewrite to eliminate C++ library dependencies
With progress reporting from MDXfind stderr output
"""

import sys
import os
import argparse
import subprocess
import tempfile
import re
import threading
import time
import signal
from pathlib import Path
from queue import Queue, Empty

# Global reference to MDXfind subprocess for signal handling
_mdxfind_process = None
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle termination signals from Hashtopolis agent"""
    global _mdxfind_process, _shutdown_requested

    signal_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
    print(f"\n[SIGNAL] Received {signal_name}, shutting down gracefully...", file=sys.stderr, flush=True)

    _shutdown_requested = True

    if _mdxfind_process and _mdxfind_process.poll() is None:
        print("[SIGNAL] Terminating MDXfind subprocess...", file=sys.stderr, flush=True)
        try:
            _mdxfind_process.terminate()
            # Give it 2 seconds to terminate gracefully
            try:
                _mdxfind_process.wait(timeout=2)
                print("[SIGNAL] MDXfind terminated gracefully", file=sys.stderr, flush=True)
            except subprocess.TimeoutExpired:
                print("[SIGNAL] MDXfind did not terminate, killing forcefully...", file=sys.stderr, flush=True)
                _mdxfind_process.kill()
                _mdxfind_process.wait()
                print("[SIGNAL] MDXfind killed", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[SIGNAL] Error terminating MDXfind: {e}", file=sys.stderr, flush=True)

    # Exit cleanly
    print("[SIGNAL] Shutdown complete, exiting", file=sys.stderr, flush=True)
    sys.exit(0)


# Register signal handlers for SIGTERM and SIGINT
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


class CrackerApp:
    """Main application class for the MDXfind wrapper"""

    def __init__(self):
        self.mdxfind_path = self._find_mdxfind()

    def _find_mdxfind(self):
        """Locate the mdxfind executable"""
        # Get the directory where this script/executable is located
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            app_dir = Path(sys.executable).parent
        else:
            # Running as script
            app_dir = Path(__file__).parent

        # Try multiple possible locations
        candidates = [
            app_dir / 'mdx_bin' / 'mdxfind',
            app_dir.parent / 'mdx_bin' / 'mdxfind',
            Path('mdx_bin') / 'mdxfind',
            Path('./mdx_bin/mdxfind'),
        ]

        for path in candidates:
            if path.exists() and path.is_file():
                return path.resolve()

        print("ERROR: MDXfind executable not found!", file=sys.stderr)
        print("Searched locations:", file=sys.stderr)
        for path in candidates:
            print(f"  - {path}", file=sys.stderr)
        sys.exit(1)

    def keyspace(self, wordlist):
        """Calculate keyspace by counting lines in wordlist"""
        if not wordlist or not Path(wordlist).exists():
            print("ERROR: Wordlist file not found", file=sys.stderr)
            return 1

        try:
            with open(wordlist, 'r', encoding='utf-8', errors='ignore') as f:
                count = sum(1 for _ in f)
            print(count)
            return 0
        except Exception as e:
            print(f"ERROR: Failed to read wordlist: {e}", file=sys.stderr)
            return 1

    def crack(self, hashlist, wordlist, hash_type='ALL,!user,salt',
              skip=0, limit=None, iterations=10, timeout=None, mdxfind_args=None, debug=False):
        """Crack hashes using MDXfind with progress reporting"""

        self.debug = debug

        if not hashlist or not Path(hashlist).exists():
            print("ERROR: Hash list file not found", file=sys.stderr)
            return 1

        if not wordlist or not Path(wordlist).exists():
            print("ERROR: Wordlist file not found", file=sys.stderr)
            return 1

        # Calculate total keyspace
        total_keyspace = limit if limit else self._count_wordlist_lines(wordlist)

        # Parse hashlist file (tab-separated: hash<TAB>salt)
        hashes, salts = self._parse_hashlist(hashlist)

        if not hashes:
            print("ERROR: No hashes found in hash list", file=sys.stderr)
            return 1

        # Use MDXfind's -w parameter for skip, no chunking needed
        # We'll monitor progress and terminate when limit is reached
        wordlist_to_use = wordlist
        mdx_skip = skip

        # Create temporary files for hashes and salts
        with tempfile.NamedTemporaryFile(mode='w', suffix='.hashes', delete=False) as hash_file, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.salts', delete=False) as salt_file:

            hash_filename = hash_file.name
            salt_filename = salt_file.name

            try:
                # Write hashes
                for h in hashes:
                    hash_file.write(h + '\n')
                hash_file.flush()

                # Write salts (always required by MDXfind, even if empty)
                for s in salts:
                    salt_file.write(s + '\n')
                salt_file.flush()

                # Build MDXfind command
                cmd = [
                    str(self.mdxfind_path),
                    '-h', hash_type,
                    '-f', hash_filename,
                    '-s', salt_filename,
                ]

                # Add skip parameter if specified (uses MDXfind's -w)
                if mdx_skip > 0:
                    cmd.extend(['-w', str(mdx_skip)])

                # Add any additional MDXfind pass-through arguments
                if mdxfind_args:
                    cmd.extend(mdxfind_args)

                # Add wordlist at the end
                cmd.append(wordlist_to_use)

                # Prepare for progress tracking
                # MDXfind reports absolute line numbers in the wordlist file
                # When skip is used, line numbers start from skip position
                progress_tracker = ProgressTracker(total_keyspace, skip)
                progress_tracker.limit = limit  # Store limit for termination check
                cracked_hashes = []

                # Declare global before assignment
                global _mdxfind_process

                try:
                    # Run MDXfind with separate stdout and stderr
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )

                    # Store process reference globally for signal handler
                    _mdxfind_process = process

                    # Setup timeout if specified
                    timeout_occurred = False
                    if timeout:
                        import signal
                        def timeout_handler(signum, frame):
                            nonlocal timeout_occurred
                            timeout_occurred = True
                            process.terminate()
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(int(timeout))

                    # Create threads to read stdout and stderr
                    stdout_queue = Queue()
                    stderr_queue = Queue()

                    stdout_thread = threading.Thread(
                        target=self._read_stream,
                        args=(process.stdout, stdout_queue, 'stdout')
                    )
                    stderr_thread = threading.Thread(
                        target=self._read_stream,
                        args=(process.stderr, stderr_queue, 'stderr')
                    )

                    stdout_thread.daemon = True
                    stderr_thread.daemon = True
                    stdout_thread.start()
                    stderr_thread.start()

                    # Main loop: process output and report status
                    last_status_time = time.time()
                    status_interval = 5  # Output STATUS every 5 seconds
                    initial_ppid = os.getppid()  # Store initial parent PID

                    while process.poll() is None or not stdout_queue.empty() or not stderr_queue.empty():
                        # Check if shutdown was requested by signal handler
                        global _shutdown_requested
                        if _shutdown_requested:
                            print("[SHUTDOWN] Shutdown requested, exiting main loop", file=sys.stderr, flush=True)
                            break

                        # Check if parent process died (orphaned) - means shell wrapper was killed
                        current_ppid = os.getppid()
                        if current_ppid != initial_ppid:
                            print(f"[PARENT-DEATH] Parent process died (PPID changed from {initial_ppid} to {current_ppid}), shutting down...", file=sys.stderr, flush=True)
                            process.terminate()
                            try:
                                process.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                            break

                        # Process stdout (cracked hashes)
                        try:
                            line = stdout_queue.get(timeout=0.1)
                            cracked = self._parse_mdxfind_output(line)
                            if cracked:
                                cracked_hashes.extend(cracked)
                                progress_tracker.add_cracked(len(cracked))
                        except Empty:
                            pass

                        # Process stderr (progress info)
                        try:
                            line = stderr_queue.get(timeout=0.1)
                            if self.debug:
                                print(f"[DEBUG STDERR] {line}", file=sys.stderr, flush=True)
                            self._parse_progress_line(line, progress_tracker)

                            # Check if we've reached the limit
                            if limit and progress_tracker.current_line >= (skip + limit):
                                if self.debug:
                                    print(f"[DEBUG] Limit reached: current_line={progress_tracker.current_line}, skip={skip}, limit={limit}", file=sys.stderr, flush=True)
                                process.terminate()
                                progress_tracker.set_complete()
                                break
                        except Empty:
                            pass

                        # Output STATUS line periodically
                        current_time = time.time()
                        if current_time - last_status_time >= status_interval:
                            if self.debug:
                                print(f"[DEBUG] Progress tracker: current_line={progress_tracker.current_line}, skip={progress_tracker.skip}, total={progress_tracker.total_keyspace}, speed={progress_tracker.speed}", file=sys.stderr, flush=True)
                            self._output_status(progress_tracker)
                            last_status_time = current_time

                    # Cancel timeout if it was set
                    if timeout:
                        signal.alarm(0)

                    # Wait for process to complete
                    process.wait()

                    # Clear global process reference
                    _mdxfind_process = None

                    # Output final STATUS
                    # Mark as complete if timeout didn't occur and not shutdown
                    if not timeout_occurred and not _shutdown_requested:
                        progress_tracker.set_complete()
                    self._output_status(progress_tracker)

                    return 0

                except Exception as e:
                    print(f"ERROR: MDXfind execution failed: {e}", file=sys.stderr)
                    # Clear global process reference on error
                    _mdxfind_process = None
                    return 1

            finally:
                # Clean up temporary files
                try:
                    os.unlink(hash_filename)
                    os.unlink(salt_filename)
                except:
                    pass

    def _count_wordlist_lines(self, wordlist):
        """Count total lines in wordlist"""
        try:
            with open(wordlist, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return 0

    def _read_stream(self, stream, queue, name):
        """Read from stream and put lines into queue"""
        try:
            for line in stream:
                queue.put(line.rstrip('\n\r'))
        except:
            pass
        finally:
            if not stream.closed:
                stream.close()

    def _parse_progress_line(self, line, tracker):
        """Parse MDXfind stderr progress line

        Format: Working on hashmob.net w=248, line 360, Found=0, 12.86Mh/s, 2.76Kc/s
        Note: Both hash rate (h/s) and candidate rate (c/s) can have K/M/G suffixes
        """
        if not line or not line.startswith('Working on'):
            return

        # Extract line number, hash rate, and candidate rate
        # Pattern: line 360, Found=0, 12.86Mh/s, 2.76Kc/s
        # Both rates can have K/M/G multipliers
        match = re.search(r'line\s+(\d+).*?Found=(\d+).*?([\d.]+)([KMG]?)h/s.*?([\d.]+)([KMG]?)c/s', line)
        if match:
            current_line = int(match.group(1))
            found_count = int(match.group(2))
            hash_rate = float(match.group(3))
            hash_unit = match.group(4)
            cand_rate = float(match.group(5))
            cand_unit = match.group(6)

            # Convert rates to base units (H/s and c/s)
            multipliers = {'K': 1000, 'M': 1000000, 'G': 1000000000, '': 1}
            hash_rate_hs = int(hash_rate * multipliers.get(hash_unit, 1))
            cand_rate_cs = int(cand_rate * multipliers.get(cand_unit, 1))

            # Update tracker with hash rate as the speed metric
            # Hashtopolis expects speed in H/s (hashes per second)
            tracker.update(current_line, hash_rate_hs, found_count)

    def _output_status(self, tracker):
        """Output Hashtopolis-compatible STATUS line

        Format: STATUS <progress> <speed>
        Where progress is 0-10000 (0.00% to 100.00%)
        """
        progress = tracker.get_progress()
        speed = tracker.get_speed()
        print(f"STATUS {progress} {speed}", flush=True)

    def _parse_hashlist(self, hashlist_file):
        """Parse Hashtopolis hash list file (tab-separated format)

        Format: hash<TAB>salt
        Each line contains a hash, followed by a tab, followed by an optional salt.
        """
        hashes = []
        salts = []

        try:
            with open(hashlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.rstrip('\n\r')
                    if not line:
                        continue

                    # Split on tab character
                    parts = line.split('\t')

                    if len(parts) >= 1:
                        hashes.append(parts[0])

                    if len(parts) >= 2:
                        salts.append(parts[1])
                    else:
                        salts.append('')  # Empty salt

            return hashes, salts

        except Exception as e:
            print(f"ERROR: Failed to parse hash list: {e}", file=sys.stderr)
            return [], []

    def _parse_mdxfind_output(self, line):
        """Parse MDXfind output line and print cracked hashes"""
        if not line:
            return []

        # Skip diagnostic/status lines
        if line.startswith('MDXfind') or \
           line.startswith('Loaded') or \
           line.startswith('Searching') or \
           line.startswith('Using') or \
           line.startswith('Hash') or \
           line.startswith('Salt') or \
           line.startswith('Reading') or \
           line.startswith('Generated') or \
           line.startswith('Took') or \
           line.startswith('Maximum') or \
           line.startswith('Minimum') or \
           line.startswith('Iterations') or \
           line.startswith('Working on') or \
           'algorithm' in line.lower() or \
           'loading' in line.lower():
            return []

        cracked = []

        # MDXfind output format: algorithm hash:plaintext
        # Example: MD5x01 5f4dcc3b5aa765d61d8327deb882cf99:password
        if ' ' in line and ':' in line:
            parts = line.split(' ', 1)
            if len(parts) == 2:
                algorithm = parts[0]
                hash_plain = parts[1]

                if ':' in hash_plain:
                    hash_parts = hash_plain.split(':', 1)
                    hash_value = hash_parts[0]
                    plaintext = hash_parts[1] if len(hash_parts) > 1 else ''
                    plaintext = plaintext.replace(':', ',')

                    # Output in Hashtopolis format: hash:plaintext:algorithm
                    output = f"{hash_value}:{algorithm},{plaintext}"
                    print(output, flush=True)
                    cracked.append(output)

        return cracked


class ProgressTracker:
    """Track progress and calculate speed for Hashtopolis reporting"""

    def __init__(self, total_keyspace, skip=0):
        self.total_keyspace = total_keyspace
        self.skip = skip
        self.current_line = skip
        self.speed = 0
        self.cracked_count = 0
        self.complete = False
        self.start_time = time.time()
        self.last_update_time = self.start_time

    def update(self, current_line, speed, found_count):
        """Update progress from MDXfind status line

        MDXfind reports absolute line numbers in the wordlist file,
        so we don't need to add skip here.
        """
        self.current_line = current_line
        self.speed = speed
        self.cracked_count = found_count
        self.last_update_time = time.time()

    def add_cracked(self, count):
        """Add to cracked hash count"""
        self.cracked_count += count

    def set_complete(self):
        """Mark processing as complete"""
        self.complete = True

    def get_progress(self):
        """Get progress as integer 0-10000 (0.00% to 100.00%)

        Uses MDXfind progress updates when available, falls back to time-based
        estimation for benchmarks where MDXfind hasn't reported yet.
        """
        if self.complete:
            return 10000

        if self.total_keyspace == 0:
            return 0

        # Calculate progress based on current line vs total
        processed = self.current_line - self.skip 
        progress = int((processed / self.total_keyspace) * 10000)
        
        # If we have MDXfind progress data, use it
        if progress > 0:
            return min(10000, progress)

        # Last resort: No data yet, return 0
        return 0

    def get_speed(self):
        """Get current speed in candidates/sec"""
        return self.speed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='MDXfind Wrapper for Hashtopolis - Hash Algorithm Identification and Cracking',
        prog='cracker'
    )

    parser.add_argument('action',
                       choices=['keyspace', 'crack'],
                       help='Action to execute (keyspace or crack)')

    # Cracker-specific arguments (not passed to MDXfind)
    parser.add_argument('-a', '--hashlist',
                       help='File containing list of hashes to attack (tab-separated: hash<TAB>salt)')

    parser.add_argument('-w', '--wordlist',
                       help='Use wordlist for attack')

    parser.add_argument('-s', '--skip',
                       type=int,
                       default=0,
                       help='Skip X first passwords in wordlist (for chunking)')

    parser.add_argument('-l', '--limit',
                       type=int,
                       help='Process X passwords from wordlist (for chunking)')

    parser.add_argument('--timeout',
                       type=int,
                       help='Stop cracking process after fixed amount of time (seconds)')

    parser.add_argument('-t', '--hash-type',
                       default='ALL,!user,salt',
                       help="Hash types for MDXfind (e.g., 'ALL,!user,salt' or 'MD5,SHA1')")

    parser.add_argument('-i', '--iterations',
                       type=int,
                       default=10,
                       help='Number of iterations for hash algorithms')

    parser.add_argument('--debug',
                       action='store_true',
                       help='Enable debug output showing MDXfind stderr and progress tracking')

    parser.add_argument('--version', action='version', version='%(prog)s 2.2 (Python)')

    # Parse known arguments, collect unknowns for MDXfind pass-through
    args, mdxfind_passthrough = parser.parse_known_args()

    # Create app instance
    app = CrackerApp()

    # Execute requested action
    if args.action == 'keyspace':
        if not args.wordlist:
            print("ERROR: --wordlist is required for keyspace action", file=sys.stderr)
            return 1
        return app.keyspace(args.wordlist)

    elif args.action == 'crack':
        if not args.hashlist:
            print("ERROR: --hashlist is required for crack action", file=sys.stderr)
            return 1
        if not args.wordlist:
            print("ERROR: --wordlist is required for crack action", file=sys.stderr)
            return 1

        return app.crack(
            hashlist=args.hashlist,
            wordlist=args.wordlist,
            hash_type=args.hash_type,
            skip=args.skip,
            limit=args.limit,
            iterations=args.iterations,
            timeout=args.timeout,
            mdxfind_args=mdxfind_passthrough,
            debug=args.debug
        )

    return 0


if __name__ == '__main__':
    sys.exit(main())
