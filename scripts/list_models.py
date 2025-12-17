from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_src_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))


def main() -> int:
    _bootstrap_src_on_path()
    from automgr.cli import main as automgr_main

    return automgr_main(["list-gemini-models", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())

