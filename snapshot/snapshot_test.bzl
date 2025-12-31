"""Snapshot testing rule."""

load(
    "//snapshot/private:test_rule.bzl",
    _snapshot_format = "snapshot_format",
    _snapshot_test = "snapshot_test",
)
load(
    "//snapshot/private:command_tool.bzl",
    _snapshot_comparator = "snapshot_comparator",
    _snapshot_normalizer = "snapshot_normalizer",
)
load("//snapshot/private:update_target.bzl", _update_all = "update_all")

snapshot_format = _snapshot_format
snapshot_normalizer = _snapshot_normalizer
snapshot_comparator = _snapshot_comparator
snapshot_test = _snapshot_test
update_all = _update_all
