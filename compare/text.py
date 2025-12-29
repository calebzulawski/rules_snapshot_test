#!/usr/bin/env python3
"""Text comparator that emits a unified diff on mismatch."""

import argparse
import difflib
import filecmp
import sys


def read_lines(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()


def main():
    parser = argparse.ArgumentParser(description="Compare normalized text against snapshots.")
    parser.add_argument("normalized", help="Path to the normalized output file.")
    parser.add_argument("snapshot", help="Path to the snapshot file.")
    args = parser.parse_args()

    if filecmp.cmp(args.normalized, args.snapshot, shallow=False):
        return 0

    normalized = read_lines(args.normalized)
    golden = read_lines(args.snapshot)

    diff = difflib.unified_diff(
        golden,
        normalized,
        fromfile=args.snapshot,
        tofile=args.normalized,
        lineterm="",
        n=3,
    )
    print("Snapshot mismatch detected:", file=sys.stderr)
    for line in diff:
        print(line, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
