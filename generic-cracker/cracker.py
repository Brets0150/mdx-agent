#!/usr/bin/env python3
"""
MDXfind Wrapper for Hashtopolis - Hash Algorithm Identification and Cracking
Python rewrite to eliminate C++ library dependencies
"""

import sys
import os
import argparse
import subprocess
import tempfile
from pathlib import Path


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
        """Crack hashes using MDXfind"""

        if not attacked_hashlist or not Path(attacked_hashlist).exists():
            print("ERROR: Hash list file not found", file=sys.stderr)
            return 1

        if not wordlist or not Path(wordlist).exists():
            print("ERROR: Wordlist file not found", file=sys.stderr)
            return 1

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

                # Run MDXfind and capture output
                cracked_count = 0

                try:
                    if timeout:
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1
                        )

                        import signal
                        def timeout_handler(signum, frame):
                            process.terminate()

                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(int(timeout))

                        for line in process.stdout:
                            cracked = self._parse_mdxfind_output(line.strip(), attacked_hashlist)
                            if cracked:
                                cracked_count += len(cracked)

                        signal.alarm(0)
                        process.wait()
                    else:
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1
                        )

                        for line in process.stdout:
                            cracked = self._parse_mdxfind_output(line.strip(), attacked_hashlist)
                            if cracked:
                                cracked_count += len(cracked)

                        process.wait()

                    # Output status for Hashtopolis
                    print(f"STATUS 10000 {cracked_count}")

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

    def _parse_mdxfind_output(self, line, hashlist_file):
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
           'algorithm' in line.lower() or \
           'loading' in line.lower():
            return []

        cracked = []

        # MDXfind output format: plaintext:hash:algorithm
        # We need format: hash:plaintext:algorithm
        if ':' in line:
            parts = line.split(':')

            if len(parts) >= 3:
                plaintext = parts[0]
                hash_value = parts[1]
                algorithm = ':'.join(parts[2:])  # Handle colons in algorithm name

                # Output in Hashtopolis format: hash:plaintext:algorithm
                output = f"{hash_value}:{plaintext}:{algorithm}"
                print(output)
                cracked.append(output)

        return cracked


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

    parser.add_argument('--version', action='version', version='%(prog)s 2.0 (Python)')

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
