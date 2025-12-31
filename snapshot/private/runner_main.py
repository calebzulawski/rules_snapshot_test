#!/usr/bin/env python3
"""Shared runner that executes tests and compares outputs against snapshots."""

import glob
import json
import os
import shutil
import subprocess
import sys

from python.runfiles import runfiles


def main():
    runfiles_ctx = runfiles.Create()
    config = load_config(runfiles_ctx)
    base_dir = resolve_base_dir()
    raw_dir, normalized_dir = prepare_output_dirs(base_dir)
    test_env = build_test_env(config["test_env"], raw_dir)
    run_wrapped_test(runfiles_ctx, config, test_env)
    process_outputs(runfiles_ctx, config, raw_dir, normalized_dir)


def load_config(runfiles_ctx):
    key = os.environ.get("SNAPSHOT_CONFIG")
    assert key, "SNAPSHOT_CONFIG is not set"
    config_path = rlocation(runfiles_ctx, key)
    with open(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_base_dir():
    base_dir = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")
    assert base_dir, "TEST_UNDECLARED_OUTPUTS_DIR is not set"
    return base_dir


def prepare_output_dirs(base_dir):
    raw_dir = os.path.join(base_dir, "raw")
    normalized_dir = os.path.join(base_dir, "normalized")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(normalized_dir, exist_ok=True)
    return raw_dir, normalized_dir


def build_test_env(config_env, raw_dir):
    env = os.environ.copy()
    env.update(config_env)
    env["TEST_UNDECLARED_OUTPUTS_DIR"] = raw_dir
    env["SNAPSHOT_OUTPUTS_DIR"] = raw_dir
    return env


def run_wrapped_test(runfiles_ctx, config, env):
    test_path = rlocation(runfiles_ctx, config["test_runfile"])
    test_cmd = [test_path] + config["test_args"]
    print("[snapshot] running test: {}".format(" ".join(test_cmd)))
    result = subprocess.run(test_cmd, env=env)
    if result.returncode != 0:
        sys.exit("[snapshot] wrapped test exited with {}".format(result.returncode))


def process_outputs(runfiles_ctx, config, raw_dir, normalized_dir):
    file_map = assign_formats(raw_dir, config["formats"])
    if not file_map:
        sys.exit("[snapshot] no files matched the configured outputs")

    for rel_path, format_cfg in sorted(file_map.items()):
        raw_path = os.path.join(raw_dir, rel_path)
        normalized_path = os.path.join(normalized_dir, rel_path)
        parent = os.path.dirname(normalized_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        run_normalizers(runfiles_ctx, raw_path, normalized_path, format_cfg["normalize"])
        snapshot_path = resolve_snapshot_path(runfiles_ctx, config, rel_path)
        run_comparator(runfiles_ctx, format_cfg, normalized_path, snapshot_path, rel_path)


def assign_formats(raw_dir, formats):
    mapping = {}
    for format_cfg in formats:
        for pattern in format_cfg["patterns"]:
            abs_pattern = os.path.join(raw_dir, pattern)
            matches = glob.glob(abs_pattern, recursive=True)
            if not matches:
                if _is_glob(pattern):
                    continue
                msg = "[snapshot] expected file {} was not produced".format(pattern)
                print(msg, file=sys.stderr)
                sys.exit(msg)
            for path in matches:
                if not os.path.isfile(path):
                    continue
                rel = os.path.relpath(path, raw_dir)
                if rel in mapping:
                    continue
                mapping[rel] = format_cfg
    return mapping


def rlocation(r, path):
    location = r.Rlocation(path)
    assert location, "missing runfile {}".format(path)
    return location


def run_normalizers(runfiles_ctx, raw_path, normalized_path, tools):
    if not tools:
        shutil.copy2(raw_path, normalized_path)
        return
    current_in = raw_path
    for index, tool in enumerate(tools):
        tool_path = rlocation(runfiles_ctx, tool["executable"])
        if index == len(tools) - 1:
            current_out = normalized_path
        else:
            current_out = normalized_path + ".stage{}".format(index)
        parent = os.path.dirname(current_out)
        if parent:
            os.makedirs(parent, exist_ok=True)
        mapping = {"{INPUT}": current_in, "{OUTPUT}": current_out}
        cmd = [tool_path] + _apply_substitutions(tool["args"], mapping)
        env = _apply_env(tool["env"], mapping)
        print("[snapshot] normalize step {}: {}".format(index, " ".join(cmd)))
        if tool.get("stdout"):
            result = subprocess.run(cmd, env=env, stdout=subprocess.PIPE)
            if result.returncode != 0:
                sys.exit(result.returncode)
            with open(current_out, "wb") as handle:
                handle.write(result.stdout)
        else:
            result = subprocess.run(cmd, env=env)
            if result.returncode != 0:
                sys.exit(result.returncode)
        if current_in not in (raw_path, normalized_path):
            if os.path.exists(current_in):
                os.remove(current_in)
        current_in = current_out


def run_comparator(runfiles_ctx, format_cfg, normalized_path, snapshot_path, rel_path):
    comparator_spec = format_cfg["compare"]
    comparator_path = rlocation(runfiles_ctx, comparator_spec["executable"])
    mapping = {
        "{OUTPUT}": normalized_path,
        "{SNAPSHOT}": snapshot_path,
    }
    cmd = [comparator_path] + _apply_substitutions(comparator_spec["args"], mapping)
    env = _apply_env(comparator_spec["env"], mapping)
    print("[snapshot] compare {} using {}: {}".format(rel_path, format_cfg["label"], " ".join(cmd)))
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print("[snapshot] comparator failed for {}".format(rel_path), file=sys.stderr)
        sys.exit("[snapshot] comparator failed for {}".format(rel_path))


def resolve_snapshot_path(r, config, rel_path):
    rel = rel_path.replace(os.sep, "/")
    prefix = config["snapshot_prefix"].rstrip("/")
    if prefix:
        key = prefix + "/" + rel
    else:
        key = rel
    return rlocation(r, key)


def _is_glob(pattern):
    return any(char in pattern for char in ["*", "?", "["])


def _apply_substitutions(values, mapping):
    result = []
    for value in values:
        expanded = value
        for key, replacement in mapping.items():
            expanded = expanded.replace(key, replacement)
        result.append(expanded)
    return result


def _apply_env(env, mapping):
    result = os.environ.copy()
    for key, value in env.items():
        expanded = value
        for token, replacement in mapping.items():
            expanded = expanded.replace(token, replacement)
        result[key] = expanded
    return result




if __name__ == "__main__":
    main()
