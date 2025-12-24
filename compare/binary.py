#!/usr/bin/env python3
"""Binary comparator that checks for byte-for-byte equality."""

import argparse
import sys


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def describe_mismatch(expected, actual):
    max_len = min(len(expected), len(actual))
    for index in range(max_len):
        if expected[index] != actual[index]:
            return index
    return max_len


def main():
    parser = argparse.ArgumentParser(description="Compare normalized binary output against snapshots.")
    parser.add_argument("normalized", help="Path to the normalized output file.")
    parser.add_argument("snapshot", help="Path to the snapshot file.")
    args = parser.parse_args()

    normalized = read_bytes(args.normalized)
    golden = read_bytes(args.snapshot)

    if normalized == golden:
        return 0

    offset = describe_mismatch(golden, normalized)
    print(
        "Binary snapshot mismatch at byte {} (snapshot size={}, normalized size={})".format(
            offset,
            len(golden),
            len(normalized),
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
