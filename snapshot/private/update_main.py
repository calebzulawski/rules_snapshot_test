#!/usr/bin/env python3
"""Updates snapshot files from the latest test outputs."""

import os
import shutil
import stat
import subprocess
import sys


def main():
    workspace = os.environ["BUILD_WORKSPACE_DIRECTORY"]

    args = sys.argv[1:]
    labels = _resolve_labels(workspace, args)

    failures = []
    for label in labels:
        try:
            _update_target(workspace, label)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            failures.append(label)

    if failures:
        sys.exit("Failed to update: {}".format(", ".join(failures)))


def _resolve_labels(workspace, args):
    labels_env = os.environ.get("SNAPSHOT_UPDATE_LABELS")
    if labels_env:
        return [label for label in labels_env.splitlines() if label.strip()]
    if args:
        return _resolve_snapshot_labels(workspace, args)
    return _resolve_snapshot_labels(workspace, ["//..."])


def _resolve_snapshot_labels(workspace, patterns):
    expr = " + ".join(patterns)
    if len(patterns) > 1:
        expr = "(" + expr + ")"
    query = "kind('_snapshot_rule_test', {})".format(expr)
    result = subprocess.run(
        ["bazel", "query", query, "--output=label"],
        cwd=workspace,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Bazel query failed: {}".format(result.stderr.strip()))
    labels = [line for line in result.stdout.splitlines() if line.strip()]
    if not labels:
        sys.exit("No snapshot_test targets matched")
    return labels


def _update_target(workspace, label):
    label = _normalize_label(label)
    if label.startswith("@"):
        raise RuntimeError("External target not supported: {}".format(label))
    if not label.startswith("//"):
        raise RuntimeError("Invalid label: {}".format(label))
    package, name = _parse_label(label)
    if not name:
        raise RuntimeError("Invalid label: {}".format(label))

    source_dir = _resolve_source_dir(workspace, package, name)
    if not os.path.isdir(source_dir):
        print("Skipping {}: test outputs not available; run the test first".format(label), file=sys.stderr)
        return

    dest_dir = _resolve_destination_dir(workspace, package, name)
    os.makedirs(dest_dir, exist_ok=True)

    copied = _copy_snapshot_outputs(source_dir, dest_dir)
    if copied == 0:
        print("Skipping {}: no outputs found under {}".format(label, source_dir), file=sys.stderr)
        return
    print(label)


def _resolve_source_dir(workspace, package, name):
    testlogs_dir = os.path.join(workspace, "bazel-testlogs")
    if package:
        testlogs_dir = os.path.join(testlogs_dir, package)
    testlogs_dir = os.path.join(testlogs_dir, name, "test.outputs")
    return os.path.join(testlogs_dir, "normalized")


def _resolve_destination_dir(workspace, package, name):
    dest_root = os.path.join(workspace, package) if package else workspace
    return os.path.join(dest_root, "snapshots", name)


def _copy_snapshot_outputs(source_dir, dest_dir):
    copied = 0
    for root, _, files in os.walk(source_dir):
        for filename in files:
            src = os.path.join(root, filename)
            rel = os.path.relpath(src, source_dir)
            dst = os.path.join(dest_dir, rel)
            parent = os.path.dirname(dst)
            if parent:
                os.makedirs(parent, exist_ok=True)
            shutil.copyfile(src, dst)
            _set_snapshot_mode(dst)
            copied += 1
    return copied


def _parse_label(label):
    value = label[2:]
    if ":" in value:
        package, name = value.split(":", 1)
    else:
        package = value
        name = value.rsplit("/", 1)[-1] if value else ""
    return package, name


def _set_snapshot_mode(path):
    try:
        mode = os.stat(path).st_mode
    except FileNotFoundError:
        return
    os.chmod(path, (mode & ~0o111) | stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def _normalize_label(label):
    if label.startswith("@@//"):
        return label[2:]
    if label.startswith("@//"):
        return label[1:]
    return label


if __name__ == "__main__":
    main()
