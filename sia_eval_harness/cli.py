"""CLI for SIA Eval Harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sia_eval_harness.compiler import write_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sia-eval",
        description="Compile reproducible SIA run receipts (harness vs weights vs overfit).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="Compile receipts from a runs/run_* directory")
    compile_p.add_argument("run_dir", type=Path, help="Path to runs/run_<id>")
    compile_p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: <run_dir>/receipts)",
    )

    args = parser.parse_args(argv)
    if args.command == "compile":
        run_dir = args.run_dir.resolve()
        if not run_dir.is_dir():
            print(f"Error: not a directory: {run_dir}", file=sys.stderr)
            return 1
        out_dir = args.output or (run_dir / "receipts")
        json_path, md_path = write_receipt(run_dir, out_dir)
        print(f"Wrote {json_path}")
        print(f"Wrote {md_path}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
