#!/usr/bin/env python3
"""Binary comparator that checks for byte-for-byte equality."""

import argparse
import filecmp
import sys


def main():
    parser = argparse.ArgumentParser(description="Compare normalized binary output against snapshots.")
    parser.add_argument("normalized", help="Path to the normalized output file.")
    parser.add_argument("snapshot", help="Path to the snapshot file.")
    args = parser.parse_args()

    if filecmp.cmp(args.snapshot, args.normalized, shallow=False):
        return 0

    print("Binary snapshot mismatch.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
