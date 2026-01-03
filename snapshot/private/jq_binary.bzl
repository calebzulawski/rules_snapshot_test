def _jq_binary_impl(ctx):
    is_windows = ctx.configuration.host_path_separator == ";"
    jq_bin = ctx.toolchains["@jq.bzl//jq/toolchain:type"].jqinfo.bin
    exe = ctx.actions.declare_file(ctx.label.name + (".exe" if is_windows else ""))
    if is_windows:
        ctx.actions.copy(output = exe, input = jq_bin, is_executable = True)
    else:
        ctx.actions.symlink(output = exe, target_file = jq_bin, is_executable = True)
    runfiles = ctx.runfiles(files = [jq_bin])
    return [DefaultInfo(
        files = depset([exe]),
        runfiles = runfiles,
        executable = exe,
    )]

jq_binary = rule(
    implementation = _jq_binary_impl,
    attrs = {},
    executable = True,
    toolchains = ["@jq.bzl//jq/toolchain:type"],
)
