#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from psi_engine.manual_check import load_manual_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the deterministic PSI Manual Check registry.")
    parser.add_argument(
        "workbook",
        nargs="?",
        default="input/PSI_Manual_Check.xlsx",
        help="Path to PSI_Manual_Check.xlsx",
    )
    args = parser.parse_args()
    path = Path(args.workbook).expanduser().resolve()
    registry = load_manual_check(path)
    print(json.dumps({"path": str(path), "status": "PASS", **registry.summary()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
