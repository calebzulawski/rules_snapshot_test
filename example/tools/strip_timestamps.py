#!/usr/bin/env python3
"""Normalizer that replaces timestamp suffixes with REDACTED."""

import argparse
from pathlib import Path
import re


TIMESTAMP_SUFFIX = re.compile(r"\s\d{4}.+$")


def normalize_line(line):
    return TIMESTAMP_SUFFIX.sub(" REDACTED", line.rstrip("\n"))


def main():
    parser = argparse.ArgumentParser(description="Strip timestamps from demo snapshot outputs.")
    parser.add_argument("raw_path")
    parser.add_argument("normalized_path")
    args = parser.parse_args()

    raw = Path(args.raw_path).read_text(encoding="utf-8").splitlines()
    cleaned = [normalize_line(line) for line in raw]
    Path(args.normalized_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.normalized_path).write_text("\n".join(cleaned) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
