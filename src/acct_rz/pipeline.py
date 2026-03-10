from __future__ import annotations

from pathlib import Path

import polars as pl

from acct_rz.features_blacklist import build_step1_blacklist_product, build_step2_traceback_product
from acct_rz.features_org_blacklist import build_org_class_blacklist_features
from acct_rz.features_windows import build_window_count_features


def run_demo_pipeline(input_path: Path, out_dir: Path) -> None:
    """运行离线演示管道。

    参数:
        input_path: 原始 Ydata CSV 路径。
        out_dir: 输出目录。

    返回:
        无，函数会写出四张结果表。

    规则:
        读取同一份原始输入，按统一事件规则产出 `step1-step4`。

    示例:
        可对 `data/demo/y.csv` 运行后查看 parquet 结果。

    实现说明:
        管道仅负责编排读写，业务规则全部收敛在变换函数内。
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    df = pl.read_csv(input_path)

    step1 = build_step1_blacklist_product(df)
    step2 = build_step2_traceback_product(df)
    step3 = build_org_class_blacklist_features(df)
    step4 = build_window_count_features(df)

    step1.write_parquet(out_dir / "step1_blacklist.parquet")
    step2.write_parquet(out_dir / "step2_traceback.parquet")
    step3.write_parquet(out_dir / "step3_org_blacklist.parquet")
    step4.write_parquet(out_dir / "step4_window_counts.parquet")

