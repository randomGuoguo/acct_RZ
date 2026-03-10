from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acct_rz.pipeline import run_demo_pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the offline Ydata feature pipeline.")
    parser.add_argument(
        "--input",
        dest="input_path",
        default="data/demo/y.csv",
        help="Input Ydata CSV path. Default: data/demo/y.csv",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default="data/result",
        help="Output directory for parquet results. Default: data/result",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    run_demo_pipeline(input_path, output_path)
    print(f"Pipeline finished. Results written to: {output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
