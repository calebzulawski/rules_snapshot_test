"""Snapshot testing rule."""

load("//snapshot/private:test_rule.bzl", _snapshot_format = "snapshot_format", _snapshot_test = "snapshot_test")

snapshot_format = _snapshot_format
snapshot_test = _snapshot_test
