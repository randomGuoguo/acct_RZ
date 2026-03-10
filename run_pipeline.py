from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acct_rz.pipeline import run_demo_pipeline
from acct_rz.query_lookup import lookup_all_steps


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the offline Ydata feature pipeline.")
    parser.add_argument(
        "--mode",
        choices=("batch", "query"),
        default="batch",
        help="Execution mode. batch builds historical outputs, query runs arbitrary lookup. Default: batch",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default="data/demo/y.csv",
        help="Historical Ydata CSV path. Default: data/demo/y.csv",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default="data/result",
        help="Output directory for parquet results. Default: data/result",
    )
    parser.add_argument(
        "--query-input",
        dest="query_input_path",
        default=None,
        help="Query CSV path used only in query mode.",
    )
    parser.add_argument(
        "--step3-format",
        dest="step3_format",
        default="long",
        help="Output format for step3 in query mode. Default: long",
    )
    return parser.parse_args(argv)


def _write_step_outputs(outputs: dict[str, pl.DataFrame], output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    outputs["step1"].write_parquet(output_path / "step1_blacklist.parquet")
    outputs["step2"].write_parquet(output_path / "step2_traceback.parquet")
    outputs["step3"].write_parquet(output_path / "step3_org_blacklist.parquet")
    outputs["step4"].write_parquet(output_path / "step4_window_counts.parquet")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)

    if args.mode == "batch":
        run_demo_pipeline(input_path, output_path)
        print(f"Pipeline finished. Results written to: {output_path.as_posix()}")
        return 0

    if not args.query_input_path:
        raise ValueError("Query mode requires --query-input.")

    history_df = pl.read_csv(input_path)
    query_df = pl.read_csv(args.query_input_path)
    outputs = lookup_all_steps(history_df, query_df, step3_format=args.step3_format)
    _write_step_outputs(outputs, output_path)
    print(f"Query lookup finished. Results written to: {output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
