load("//snapshot/private:update_rule.bzl", "snapshot_update_rule")


def snapshot_update_target(name, visibility = None):
    snapshot_update_rule(
        name = name,
        visibility = visibility,
    )


def update_all(name, visibility = None, testonly = True):
    """Create a script that updates all snapshots in this package."""
    labels = []
    for rule_name, rule in native.existing_rules().items():
        if rule.get("kind") == "_snapshot_rule_test":
            labels.append(":" + rule_name)
    if not labels:
        fail("update_all found no snapshot_test targets in this package")

    snapshot_update_rule(
        name = name,
        labels = labels,
        testonly = testonly,
        visibility = visibility,
    )
