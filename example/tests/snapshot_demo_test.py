import os
import json
from pathlib import Path

from app import report


def main():
    output_root = os.environ.get("SNAPSHOT_OUTPUTS_DIR")
    if not output_root:
        raise SystemExit("SNAPSHOT_OUTPUTS_DIR must be set")

    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = report.generate_lines()
    timestamps = report.generate_timestamps()
    (output_dir / "data.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (output_dir / "data.json").write_text(
        json.dumps(
            {
                "timestamps": {
                    "utc": timestamps["utc"].isoformat().replace("+00:00", "Z"),
                    "est": timestamps["est"].isoformat(),
                },
                "count": len(lines),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
