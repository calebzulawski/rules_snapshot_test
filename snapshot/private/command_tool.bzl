def _rlocation(ctx, target):
    return ctx.expand_location("$(rlocationpath %s)" % target.label, [target])

def _merge_runfiles(base, target):
    info = target[DefaultInfo]
    return base.merge(info.default_runfiles)

def _expand_value(ctx, value, deps):
    expanded = ctx.expand_make_variables(ctx.label.name, value, ctx.var)
    return ctx.expand_location(expanded, deps)

SnapshotCommandInfo = provider(
    fields = ["executable", "args", "env", "stdout"],
)

def _snapshot_command_impl(ctx, allow_stdout):
    deps_for_expansion = [ctx.attr.executable]
    deps_for_expansion.extend(ctx.attr.data)

    args = [_expand_value(ctx, arg, deps_for_expansion) for arg in ctx.attr.args]
    env = {}
    for key, value in ctx.attr.env.items():
        env[key] = _expand_value(ctx, value, deps_for_expansion)

    if hasattr(ctx.attr, "stdout"):
        stdout = getattr(ctx.attr, "stdout")
    else:
        stdout = False

    runfiles = ctx.runfiles()
    runfiles = _merge_runfiles(runfiles, ctx.attr.executable)
    runfiles = runfiles.merge(ctx.runfiles(files = ctx.files.data))
    for dep in ctx.attr.data:
        runfiles = _merge_runfiles(runfiles, dep)

    return [
        DefaultInfo(runfiles = runfiles),
        SnapshotCommandInfo(
            executable = _rlocation(ctx, ctx.attr.executable),
            args = args,
            env = env,
            stdout = stdout,
        ),
    ]

def _snapshot_normalizer_impl(ctx):
    return _snapshot_command_impl(ctx, allow_stdout = True)

def _snapshot_comparator_impl(ctx):
    return _snapshot_command_impl(ctx, allow_stdout = False)

snapshot_normalizer = rule(
    implementation = _snapshot_normalizer_impl,
    doc = """Define a snapshot normalizer, which reads a test output file, applies normalization, and writes the normalized output file.

A normalizer can be used to remove unstable outputs or make a file easier to compare. Some examples include removing timestamps, sorting JSON keys, or converting a binary file to a textual representation.
""",
    attrs = {
        "executable": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "The executable to run.",
        ),
        "args": attr.string_list(
            doc = "Arguments to pass to to the executable. Supports Make variable expansion. Also expands special `{INPUT}` and `{OUTPUT}` templates with the actual input and output file paths.",
        ),
        "env": attr.string_dict(
            doc = "Environment variables to pass to to the executable. Supports Make variable expansion. Also expands special `{INPUT}` and `{OUTPUT}` templates with the actual input and output file paths.",
        ),
        "data": attr.label_list(
            allow_files = True,
            doc = "The list of files needed by this target at runtime",
        ),
        "stdout": attr.bool(
            default = False,
            doc = "Capture stdout and write it to the normalized output file.",
        ),
    },
)

snapshot_comparator = rule(
    implementation = _snapshot_comparator_impl,
    doc = "Define a snapshot comparator, which reads the test output file and snapshot file, compares them, and returns a non-zero exit code if they don't match",
    attrs = {
        "executable": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "The executable to run.",
        ),
        "args": attr.string_list(
            doc = "Arguments to pass to to the executable. Supports Make variable expansion. Also expands special `{OUTPUT}` and `{SNAPSHOT}` templates with the actual test output and snapshot file paths.",
        ),
        "env": attr.string_dict(
            doc = "Environment variables to pass to to the executable. Supports Make variable expansion. Also expands special `{INPUT}` and `{OUTPUT}` templates with the actual input and output file paths.",
        ),
        "data": attr.label_list(
            allow_files = True,
            doc = "The list of files needed by this target at runtime",
        ),
    },
)
