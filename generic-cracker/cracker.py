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
from pathlib import Path
from queue import Queue, Empty


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

    def crack(self, attacked_hashlist, wordlist, hash_type='ALL,!user,salt',
              skip=0, length=None, iterations=10, timeout=None):
        """Crack hashes using MDXfind with progress reporting"""

        if not attacked_hashlist or not Path(attacked_hashlist).exists():
            print("ERROR: Hash list file not found", file=sys.stderr)
            return 1

        if not wordlist or not Path(wordlist).exists():
            print("ERROR: Wordlist file not found", file=sys.stderr)
            return 1

        # Calculate total keyspace
        total_keyspace = length if length else self._count_wordlist_lines(wordlist)

        # Parse hash file and separate hashes from salts
        hashes, salts = self._parse_hashlist(attacked_hashlist)

        if not hashes:
            print("ERROR: No hashes found in hash list", file=sys.stderr)
            return 1

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
                    '-i', str(iterations),
                    '-q', str(iterations),
                    '-f', hash_filename,
                    '-s', salt_filename,
                    '-e',  # Extended search for truncated hashes
                    wordlist
                ]

                # Add skip parameter if specified
                if skip > 0:
                    cmd.extend(['-w', str(skip)])

                # Prepare for progress tracking
                progress_tracker = ProgressTracker(total_keyspace, skip)
                cracked_hashes = []

                try:
                    # Run MDXfind with separate stdout and stderr
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )

                    # Setup timeout if specified
                    if timeout:
                        import signal
                        def timeout_handler(signum, frame):
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

                    while process.poll() is None or not stdout_queue.empty() or not stderr_queue.empty():
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
                            self._parse_progress_line(line, progress_tracker)
                        except Empty:
                            pass

                        # Output STATUS line periodically
                        current_time = time.time()
                        if current_time - last_status_time >= status_interval:
                            self._output_status(progress_tracker)
                            last_status_time = current_time

                    # Cancel timeout if it was set
                    if timeout:
                        signal.alarm(0)

                    # Wait for process to complete
                    process.wait()

                    # Output final STATUS
                    progress_tracker.set_complete()
                    self._output_status(progress_tracker)

                    return 0

                except Exception as e:
                    print(f"ERROR: MDXfind execution failed: {e}", file=sys.stderr)
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
        """Parse hash list file and extract hashes and salts"""
        hashes = []
        salts = []

        try:
            with open(hashlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # Format: hash:salt:plaintext or hash:salt or hash
                    parts = line.split(':')

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

                    # Output in Hashtopolis format: hash:plaintext:algorithm
                    output = f"{hash_value}:{plaintext}:{algorithm}"
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
        """Update progress from MDXfind status line"""
        self.current_line = current_line + self.skip
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
        """Get progress as integer 0-10000 (0.00% to 100.00%)"""
        if self.complete:
            return 10000

        if self.total_keyspace == 0:
            return 0

        # Calculate progress based on current line vs total
        processed = self.current_line - self.skip
        progress = int((processed / self.total_keyspace) * 10000)
        return min(10000, max(0, progress))

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

    parser.add_argument('-m', '--mask',
                       help='Use mask for attack')

    parser.add_argument('-w', '--wordlist',
                       help='Use wordlist for attack')

    parser.add_argument('-a', '--attacked-hashlist',
                       help='File containing list of hashes to attack')

    parser.add_argument('-s', '--skip',
                       type=int,
                       default=0,
                       help='Skip X first passwords in wordlist')

    parser.add_argument('-l', '--length',
                       type=int,
                       help='Crack X first passwords in wordlist')

    parser.add_argument('--timeout',
                       type=int,
                       help='Stop cracking process after fixed amount of time (seconds)')

    parser.add_argument('-t', '--type',
                       default='ALL,!user,salt',
                       help="Hash types for MDXfind (e.g., 'ALL,!user,salt' or 'MD5,SHA1')")

    parser.add_argument('-i', '--iterations',
                       type=int,
                       default=10,
                       help='Number of iterations for hash algorithms')

    parser.add_argument('--version', action='version', version='%(prog)s 2.1 (Python)')

    # Parse arguments, but allow unknown options for Hashtopolis compatibility
    args, unknown = parser.parse_known_args()

    # Create app instance
    app = CrackerApp()

    # Execute requested action
    if args.action == 'keyspace':
        if not args.wordlist:
            print("ERROR: --wordlist is required for keyspace action", file=sys.stderr)
            return 1
        return app.keyspace(args.wordlist)

    elif args.action == 'crack':
        if not args.attacked_hashlist:
            print("ERROR: --attacked-hashlist is required for crack action", file=sys.stderr)
            return 1
        if not args.wordlist:
            print("ERROR: --wordlist is required for crack action", file=sys.stderr)
            return 1

        return app.crack(
            attacked_hashlist=args.attacked_hashlist,
            wordlist=args.wordlist,
            hash_type=args.type,
            skip=args.skip,
            length=args.length,
            iterations=args.iterations,
            timeout=args.timeout
        )

    return 0


if __name__ == '__main__':
    sys.exit(main())
