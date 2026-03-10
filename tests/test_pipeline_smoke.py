import shutil
from pathlib import Path

import polars as pl

from acct_rz.pipeline import run_demo_pipeline


def test_run_demo_pipeline_writes_outputs() -> None:
    out_dir = Path("tests/.tmp_outputs")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    run_demo_pipeline(Path("data/demo/y.csv"), out_dir)

    assert (out_dir / "step1_blacklist.parquet").exists()
    assert (out_dir / "step2_traceback.parquet").exists()
    assert (out_dir / "step3_org_blacklist.parquet").exists()
    assert (out_dir / "step4_window_counts.parquet").exists()

    step1 = pl.read_parquet(out_dir / "step1_blacklist.parquet")
    assert {"app_dt", "key_type", "key_value", "PID", "ID", "black_hit_ever"}.issubset(set(step1.columns))
    assert step1.schema["app_dt"] == pl.Int64
    assert step1.schema["first_default_event_dt"] == pl.Int64
    shutil.rmtree(out_dir)
