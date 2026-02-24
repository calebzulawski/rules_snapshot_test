def runfile_repo(ctx, target):
    return target.label.workspace_name or ctx.workspace_name or "_main"

def runfile_path(ctx, target, file):
    short_path = file.short_path
    if short_path.startswith("../"):
        return short_path.removeprefix("../")
    return "{}/{}".format(runfile_repo(ctx, target), short_path)

def executable_runfile_path(ctx, target):
    executable = target[DefaultInfo].files_to_run.executable
    if not executable:
        fail("target '{}' must be executable".format(target.label))
    return runfile_path(ctx, target, executable)
