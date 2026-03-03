load("//snapshot/private:update_rule.bzl", "snapshot_update_rule")


def snapshot_update_target(name, visibility = None):
    snapshot_update_rule(
        name = name,
        visibility = visibility,
    )


def update_all(name, visibility = None, testonly = True, recursive = False):
    """Create a script that updates snapshot tests in this package.

    Args:
      recursive: If True, also update snapshot tests in subpackages.
    """
    package = native.package_name()
    if recursive:
        pattern = "//{}...".format(package + "/" if package else "")
    else:
        pattern = "//{}:*".format(package) if package else "//:*"

    snapshot_update_rule(
        name = name,
        patterns = [pattern],
        testonly = testonly,
        visibility = visibility,
    )
