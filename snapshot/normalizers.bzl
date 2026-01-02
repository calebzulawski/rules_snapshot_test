"""Snapshot normalizer helpers."""

load("//snapshot/private:command_tool.bzl", "snapshot_normalizer")


def text_normalizer(
        name,
        replace_text = None,
        line_ending = None,
        include_lines = None,
        exclude_lines = None,
        **kwargs):
    """Define a snapshot normalizer that applies streaming text transforms.

    Args:
        name: Target name.
        replace_text: Map of regex patterns to replacement strings (Python re.sub semantics).
        line_ending: Optional line ending normalization: "unix", "windows", or None.
        include_lines: List of regex patterns; only matching lines are kept.
        exclude_lines: List of regex patterns; matching lines are removed.
        **kwargs: Extra attributes forwarded to `snapshot_normalizer`.
    """
    if line_ending and line_ending not in ["unix", "windows"]:
        fail("line_ending must be 'unix', 'windows', or None")
    tool_label = Label("//snapshot/private:text_normalizer")
    def _escape_make(value):
        return value.replace("$", "$$")
    args = ["{INPUT}", "{OUTPUT}"]
    if line_ending == "unix":
        args.extend(["--replace-text", r"\r", ""])
    elif line_ending == "windows":
        args.extend(["--replace-text", r"(?<!\r)\n", "\r\n"])
        args.extend(["--replace-text", r"\r(?!\n)", "\r\n"])
    for pattern, replacement in (replace_text or {}).items():
        args.extend(["--replace-text", _escape_make(pattern), _escape_make(replacement)])
    for pattern in include_lines or []:
        args.extend(["--include-line", _escape_make(pattern)])
    for pattern in exclude_lines or []:
        args.extend(["--exclude-line", _escape_make(pattern)])

    snapshot_normalizer(
        name = name,
        executable = tool_label,
        args = args,
        **kwargs
    )
