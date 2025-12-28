load("//snapshot/private:update_rule.bzl", "snapshot_update_rule")


def snapshot_update_target(name, visibility = None):
    snapshot_update_rule(
        name = name,
        visibility = visibility,
    )
