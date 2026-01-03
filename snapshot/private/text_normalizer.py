#!/usr/bin/env python3
"""Streaming text normalizer for snapshot outputs."""

import argparse
import re


def _compile_replacements(values):
    compiled = []
    for pattern, replacement in values:
        compiled.append((re.compile(pattern.encode("utf-8")), replacement.encode("utf-8")))
    return compiled


def _compile_patterns(values):
    return [re.compile(value.encode("utf-8")) for value in values]


def _split_line(line):
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith(b"\n") or line.endswith(b"\r"):
        return line[:-1], line[-1:]
    return line, b""

def main():
    parser = argparse.ArgumentParser(description="Normalize snapshot text outputs.")
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    parser.add_argument(
        "--replace-text",
        action="append",
        nargs=2,
        metavar=("PATTERN", "REPLACEMENT"),
        default=[],
        help="Regex pattern and replacement text.",
    )
    parser.add_argument(
        "--include-line",
        action="append",
        default=[],
        help="Keep lines matching any pattern.",
    )
    parser.add_argument(
        "--exclude-line",
        action="append",
        default=[],
        help="Drop lines matching any pattern.",
    )
    parser.add_argument(
        "--line-ending",
        choices=["unix", "windows", "none"],
        default="none",
        help="Normalize line endings.",
    )
    args = parser.parse_args()

    if args.line_ending == "unix":
        replacement_newline = b"\n"
    elif args.line_ending == "windows":
        replacement_newline = b"\r\n"
    else:
        replacement_newline = None

    replace_patterns = _compile_replacements(args.replace_text)
    include_patterns = _compile_patterns(args.include_line)
    exclude_patterns = _compile_patterns(args.exclude_line)

    with open(args.input_path, "rb") as infile, open(args.output_path, "wb") as outfile:
        for line in infile:
            content, newline = _split_line(line)
            for pattern, replacement in replace_patterns:
                content = pattern.sub(replacement, content)
            if include_patterns and not any(p.search(content) for p in include_patterns):
                continue
            if exclude_patterns and any(p.search(content) for p in exclude_patterns):
                continue
            if replacement_newline is not None:
                newline = replacement_newline
            outfile.write(content + newline)


if __name__ == "__main__":
    main()
