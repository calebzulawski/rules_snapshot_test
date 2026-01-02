#!/usr/bin/env python3
"""Shared runner that executes tests and compares outputs against snapshots."""

import glob
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from python.runfiles import runfiles


def main():
    runfiles_ctx = runfiles.Create()
    config = load_config(runfiles_ctx)
    base_dir = resolve_base_dir()
    raw_dir, normalized_dir, results_dir = prepare_output_dirs(base_dir)
    test_env = build_test_env(config["test_env"], raw_dir)
    run_wrapped_test(runfiles_ctx, config, test_env)
    total, failures, results = process_outputs(
        runfiles_ctx,
        config,
        raw_dir,
        normalized_dir,
        results_dir,
    )
    write_junit_report(config, results)
    print_failure_summary(failures, total)
    if failures:
        sys.exit(1)


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
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(normalized_dir, exist_ok=True)
    return raw_dir, normalized_dir, results_dir


def build_test_env(config_env, raw_dir):
    env = os.environ.copy()
    env.update(config_env)
    env["TEST_UNDECLARED_OUTPUTS_DIR"] = raw_dir
    env["SNAPSHOT_OUTPUTS_DIR"] = raw_dir
    return env


def run_wrapped_test(runfiles_ctx, config, env):
    test_path = rlocation(runfiles_ctx, config["test_runfile"])
    test_cmd = [test_path] + config["test_args"]
    result = subprocess.run(test_cmd, env=env)
    if result.returncode != 0:
        sys.exit("[snapshot] wrapped test exited with {}".format(result.returncode))


def process_outputs(runfiles_ctx, config, raw_dir, normalized_dir, results_dir):
    file_map = assign_formats(raw_dir, config["formats"])
    if not file_map:
        sys.exit("[snapshot] no files matched the configured outputs")

    failures = []
    results = []
    for rel_path, format_cfg in sorted(file_map.items()):
        display_name = format_cfg["display_name"]
        raw_path = os.path.join(raw_dir, rel_path)
        normalized_path = os.path.join(normalized_dir, rel_path)
        parent = os.path.dirname(normalized_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        snapshot_path = resolve_snapshot_path(runfiles_ctx, config, rel_path)
        normalize_ok, normalize_result = run_normalizers(
            runfiles_ctx,
            raw_path,
            normalized_path,
            format_cfg["normalize"],
            rel_path,
            display_name,
            results_dir,
        )
        if not normalize_ok:
            failures.append(normalize_result)
            results.append(_build_result(rel_path, display_name, normalize_result))
            _print_failure(normalize_result)
            continue
        compare_ok, compare_result = run_comparator(
            runfiles_ctx,
            format_cfg,
            normalized_path,
            snapshot_path,
            rel_path,
            display_name,
            results_dir,
        )
        if compare_ok:
            results.append(_build_result(rel_path, display_name, None))
        else:
            failures.append(compare_result)
            results.append(_build_result(rel_path, display_name, compare_result))
            _print_failure(compare_result)
    return len(file_map), failures, results


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


def run_normalizers(
    runfiles_ctx,
    raw_path,
    normalized_path,
    tools,
    rel_path,
    display_name,
    results_dir,
):
    if not tools:
        shutil.copy2(raw_path, normalized_path)
        return True, None
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
        result = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            _write_failure_log(results_dir, rel_path, result.stdout, result.stderr)
            return False, {
                "rel_path": rel_path,
                "display_name": display_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "failure_kind": "normalize",
            }
        if tool.get("stdout"):
            with open(current_out, "wb") as handle:
                handle.write(result.stdout)
        if current_in not in (raw_path, normalized_path):
            if os.path.exists(current_in):
                os.remove(current_in)
        current_in = current_out
    return True, None


def run_comparator(
    runfiles_ctx,
    format_cfg,
    normalized_path,
    snapshot_path,
    rel_path,
    display_name,
    results_dir,
):
    comparator_spec = format_cfg["compare"]
    comparator_path = rlocation(runfiles_ctx, comparator_spec["executable"])
    mapping = {
        "{OUTPUT}": os.path.relpath(normalized_path),
        "{SNAPSHOT}": os.path.relpath(snapshot_path),
    }
    cmd = [comparator_path] + _apply_substitutions(comparator_spec["args"], mapping)
    env = _apply_env(comparator_spec["env"], mapping)
    result = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        _write_failure_log(results_dir, rel_path, result.stdout, result.stderr)
        return False, {
            "rel_path": rel_path,
            "display_name": display_name,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "failure_kind": "compare",
        }
    return True, None


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




def _write_failure_log(results_dir, rel_path, stdout, stderr):
    log_path = os.path.join(results_dir, rel_path + ".log")
    parent = os.path.dirname(log_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(log_path, "wb") as handle:
        if stdout:
            handle.write(b"\n--- stdout ---\n")
            handle.write(stdout)
        if stderr:
            handle.write(b"\n--- stderr ---\n")
            handle.write(stderr)


def _print_failure(failure):
    display_name = failure["display_name"]
    print("FAILED: {} ({})".format(failure["rel_path"], display_name))
    output = _combine_output(failure.get("stdout"), failure.get("stderr"))
    output = _truncate_output(output)
    if output:
        print(output.rstrip())
    print("-" * 80)


def print_failure_summary(failures, total):
    if failures:
        print("Failed snapshots:")
        for failure in failures:
            print("- {} ({})".format(failure["display_name"], failure["rel_path"]))
    failed = len(failures)
    summary = "[{}/{}] snapshot files".format(failed, total)
    print(summary)


def _combine_output(stdout, stderr):
    output = b""
    if stdout:
        output += stdout
    if stderr:
        if output:
            output += b"\n"
        output += stderr
    if not output:
        return ""
    return output.decode("utf-8", errors="replace")


def _truncate_output(output):
    if not output:
        return ""
    lines = output.splitlines()
    if len(lines) <= 6:
        return output
    head = lines[:3]
    tail = lines[-3:]
    return "\n".join(head + ["..."] + tail)


def _build_result(rel_path, display_name, failure):
    result = {
        "rel_path": rel_path,
        "display_name": display_name,
        "status": "pass",
    }
    if failure:
        result["status"] = "fail"
        result["stdout"] = failure.get("stdout")
        result["stderr"] = failure.get("stderr")
        result["failure_kind"] = failure.get("failure_kind") or "failed"
    return result


def write_junit_report(config, results):
    output_path = os.environ.get("XML_OUTPUT_FILE")
    if not output_path:
        return
    suite_name = os.environ.get("TEST_TARGET", "").strip() or config.get("test_name") or "snapshot"
    suite = ET.Element(
        "testsuite",
        name=suite_name,
        tests=str(len(results)),
        failures=str(sum(1 for r in results if r["status"] == "fail")),
    )
    for result in results:
        testcase = ET.SubElement(
            suite,
            "testcase",
            classname=result["display_name"],
            name=result["rel_path"],
        )
        if result["status"] == "fail":
            message = "{} failed".format(result.get("failure_kind", "test"))
            failure = ET.SubElement(testcase, "failure", message=message)
            output_text = _combine_output(result.get("stdout"), result.get("stderr"))
            failure.text = output_text
    tree = ET.ElementTree(suite)
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)






if __name__ == "__main__":
    main()
