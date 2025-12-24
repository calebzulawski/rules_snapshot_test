import os
from pathlib import Path

from app import report


def main():
    output_root = os.environ.get("SNAPSHOT_OUTPUTS_DIR")
    if not output_root:
        raise SystemExit("SNAPSHOT_OUTPUTS_DIR must be set")

    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = report.generate_lines()
    (output_dir / "data.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
