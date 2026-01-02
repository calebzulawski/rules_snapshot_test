load("//snapshot/private:update_rule.bzl", "snapshot_update_rule")
load("//snapshot/private:command_tool.bzl", "SnapshotCommandInfo")

def _rlocation(ctx, target):
    return ctx.expand_location("$(rlocationpath %s)" % target.label, [target])

def _gather_runfiles(ctx, extra_files):
    runfiles = ctx.runfiles(files = extra_files)

    def _merge(base, target):
        if not target:
            return base
        info = target[DefaultInfo]
        return base.merge(info.default_runfiles)

    runfiles = _merge(runfiles, ctx.attr._runner)
    runfiles = _merge(runfiles, ctx.attr.test)

    for dep in ctx.attr.data:
        runfiles = _merge(runfiles, dep)

    for format_target in ctx.attr.outputs.values():
        runfiles = _merge(runfiles, format_target)
        info = format_target[_SnapshotFormatInfo]
        for tool in info.normalize or []:
            runfiles = _merge(runfiles, tool)
        runfiles = _merge(runfiles, info.compare)

    return runfiles.merge(ctx.runfiles(files = ctx.files.snapshots))

_SnapshotFormatInfo = provider(fields = ["normalize", "compare", "display_name"])

def _snapshot_format_impl(ctx):
    display_name = ctx.attr.display_name or ctx.label.name
    return [
        _SnapshotFormatInfo(
            normalize = ctx.attr.normalize,
            compare = ctx.attr.compare,
            display_name = display_name,
        ),
    ]

def _normalizer_spec(ctx, target):
    if SnapshotCommandInfo in target:
        info = target[SnapshotCommandInfo]
        return {
            "executable": info.executable,
            "args": info.args,
            "env": info.env,
            "stdout": info.stdout,
        }
    return {
        "executable": _rlocation(ctx, target),
        "args": ["{INPUT}", "{OUTPUT}"],
        "env": {},
        "stdout": False,
    }

def _comparator_spec(ctx, target):
    if SnapshotCommandInfo in target:
        info = target[SnapshotCommandInfo]
        return {
            "executable": info.executable,
            "args": info.args,
            "env": info.env,
            "stdout": False,
        }
    return {
        "executable": _rlocation(ctx, target),
        "args": ["{SNAPSHOT}", "{OUTPUT}"],
        "env": {},
        "stdout": False,
    }

snapshot_format = rule(
    implementation = _snapshot_format_impl,
    doc = "Defines the normalization and comparison tools used for a set of snapshot files.",
    attrs = {
        "display_name": attr.string(
            doc = "Display name used in test output. Defaults to the snapshot_format rule name.",
        ),
        "normalize": attr.label_list(
            allow_files = True,
            cfg = "exec",
            doc = "Executable targets or snapshot_normalizer rules run sequentially on each matched file, preprocessing the file for comparison.",
        ),
        "compare": attr.label(
            cfg = "exec",
            doc = "Executable target or snapshot_comparator rule that compares each test output to its snapshot.",
        ),
    },
)

def _build_config(ctx):
    deps_for_expansion = [ctx.attr.test]
    deps_for_expansion.extend(ctx.attr.data)

    formats = []
    for pattern, format_target in ctx.attr.outputs.items():
        info = format_target[_SnapshotFormatInfo]
        normalize_targets = info.normalize or []
        compare_target = info.compare
        if compare_target == None:
            fail("snapshot_format '{}' must set a compare tool".format(format_target.label))

        normalize_paths = [_normalizer_spec(ctx, target) for target in normalize_targets]
        compare_path = _comparator_spec(ctx, compare_target)
        formats.append({
            "display_name": info.display_name,
            "patterns": [pattern],
            "normalize": normalize_paths,
            "compare": compare_path,
        })

        deps_for_expansion.append(format_target)
        deps_for_expansion.extend(normalize_targets)
        deps_for_expansion.append(compare_target)

    snapshot_repo = ctx.workspace_name or "_main"
    snapshot_package = ctx.label.package
    snapshot_dir = "snapshots/%s" % ctx.label.name
    snapshot_root_parts = []
    if snapshot_package:
        snapshot_root_parts.append(snapshot_package.strip("/"))
    snapshot_root_parts.append(snapshot_dir.strip("/"))
    snapshot_rel_root = "/".join(snapshot_root_parts)
    snapshot_parts = []
    if snapshot_repo:
        snapshot_parts.append(snapshot_repo.strip("/"))
    if snapshot_package:
        snapshot_parts.append(snapshot_package.strip("/"))
    snapshot_parts.append(snapshot_dir.strip("/"))
    snapshot_prefix = "/".join(snapshot_parts)
    return {
        "test_runfile": _rlocation(ctx, ctx.attr.test),
        "test_args": _expand_args(ctx, deps_for_expansion),
        "test_env": _expand_env(ctx, deps_for_expansion),
        "formats": formats,
        "snapshot_prefix": snapshot_prefix,
        "snapshot_rel_root": snapshot_rel_root,
        "test_package": ctx.attr.test.label.package,
        "test_name": ctx.attr.test.label.name,
    }

def _expand_args(ctx, deps):
    if not ctx.attr.args:
        return []
    return [ctx.expand_location(arg, deps) for arg in ctx.attr.args]

def _expand_env(ctx, deps):
    if not ctx.attr.env:
        return {}
    expanded = {}
    for key, value in ctx.attr.env.items():
        expanded[key] = ctx.expand_location(value, deps)
    return expanded

def _snapshot_rule_test_impl(ctx):
    config = _build_config(ctx)
    config_literal = json.encode(config)
    config_file = ctx.actions.declare_file(ctx.label.name + "_config.json")
    ctx.actions.write(config_file, config_literal + "\n")

    runfiles = _gather_runfiles(ctx, extra_files = [config_file])
    runner_outputs = _symlink_runner_files(ctx)
    launcher = runner_outputs.executable

    return [
        DefaultInfo(
            executable = launcher,
            files = depset(runner_outputs.files),
            runfiles = runfiles,
        ),
        testing.TestEnvironment({
            "SNAPSHOT_CONFIG": "{}/{}".format(ctx.workspace_name, config_file.short_path),
        }),
    ]

_snapshot_rule_test = rule(
    implementation = _snapshot_rule_test_impl,
    test = True,
    attrs = {
        "test": attr.label(
            mandatory = True,
            executable = True,
            cfg = "target",
        ),
        "outputs": attr.string_keyed_label_dict(
            providers = [_SnapshotFormatInfo],
        ),
        "snapshots": attr.label_list(
            allow_files = True,
        ),
        "data": attr.label_list(),
        "env": attr.string_dict(),
        "_runner": attr.label(
            executable = True,
            cfg = "target",
            default = Label("//snapshot/private:runner"),
        ),
    },
)

def _symlink_runner_files(ctx):
    runner_info = ctx.attr._runner[DefaultInfo]
    all_files = runner_info.files.to_list() + runner_info.default_runfiles.files.to_list()
    executable = ctx.executable._runner
    zip_file = None
    for file in all_files:
        if file.basename.lower().endswith(".zip"):
            zip_file = file
            break
    outputs = []
    exec_output = ctx.actions.declare_file("{}_{}".format(ctx.label.name, executable.basename))
    ctx.actions.symlink(output = exec_output, target_file = executable)
    outputs.append(exec_output)
    if zip_file:
        zip_output = ctx.actions.declare_file("{}_{}".format(ctx.label.name, zip_file.basename))
        ctx.actions.symlink(output = zip_output, target_file = zip_file)
        outputs.append(zip_output)
    return struct(
        executable = exec_output,
        files = outputs,
    )

def snapshot_test(name, **kwargs):
    """
    Create a snapshot test.

    Args:
      test: Executable test target that writes its outputs to SNAPSHOT_OUTPUTS_DIR.
      outputs: Mapping from output path globs to snapshot_format targets.
      data: The list of files needed at runtime.
      args: Arguments passed to `test`.
      env: Environment variables passed to `test`.

    Also creates a target named `{name}.update` that invokes the snapshot updater
    for this test.
    """
    snapshot_subdir = "snapshots/" + name
    snapshot_files = native.glob(
        include = [snapshot_subdir + "/**"],
        allow_empty = True,
    )

    _snapshot_rule_test(
        name = name,
        snapshots = snapshot_files,
        **kwargs
    )

    snapshot_update_rule(
        name = name + ".update",
        labels = [":" + name],
        testonly = kwargs.get("testonly", True),
        visibility = kwargs.get("visibility"),
    )
