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
    for pattern, replacement in (replace_text or {}).items():
        args.extend(["--replace-text", _escape_make(pattern), _escape_make(replacement)])
    if line_ending == "unix":
        args.extend(["--line-ending", "unix"])
    elif line_ending == "windows":
        args.extend(["--line-ending", "windows"])
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


def json_normalizer(
        name,
        filter = None,
        filter_file = None,
        args = None,
        data = None,
        **kwargs):
    """Define a snapshot normalizer that applies jq filters to JSON output.

    Args:
        name: Target name.
        filter: jq filter expression.
        filter_file: File containing a jq filter expression.
        args: Additional args passed to jq.
        data: Runtime files made available to the normalizer.
        **kwargs: Extra attributes forwarded to `snapshot_normalizer`.
    """
    if filter and filter_file:
        fail("json_normalizer: set only one of filter or filter_file")
    def _escape_make(value):
        return value.replace("$", "$$")
    tool_label = Label("//snapshot/private:jq")
    norm_args = []
    norm_args.extend([_escape_make(arg) for arg in (args or [])])
    if filter_file:
        norm_args.extend(["-f", "$(rlocationpath %s)" % filter_file])
    else:
        norm_args.append(_escape_make(filter or "."))
    norm_args.append("{INPUT}")

    extra_data = list(data or [])
    if filter_file:
        extra_data.append(filter_file)

    snapshot_normalizer(
        name = name,
        executable = tool_label,
        args = norm_args,
        data = extra_data,
        stdout = True,
        **kwargs
    )
