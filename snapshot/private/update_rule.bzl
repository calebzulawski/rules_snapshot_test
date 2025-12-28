def _snapshot_update_impl(ctx):
    launcher = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.symlink(
        output = launcher,
        target_file = ctx.executable._updater,
        is_executable = True,
    )

    runfiles = ctx.runfiles(files = [ctx.executable._updater])
    runfiles = runfiles.merge(ctx.attr._updater[DefaultInfo].default_runfiles)

    env = {}
    if ctx.attr.labels:
        env["SNAPSHOT_UPDATE_LABELS"] = "\n".join([str(target.label) for target in ctx.attr.labels])

    return [
        DefaultInfo(executable = launcher, runfiles = runfiles),
        RunEnvironmentInfo(environment = env),
    ]


snapshot_update_rule = rule(
    implementation = _snapshot_update_impl,
    executable = True,
    attrs = {
        "labels": attr.label_list(),
        "_updater": attr.label(
            executable = True,
            cfg = "target",
            default = Label("//snapshot/private:update"),
        ),
    },
)
