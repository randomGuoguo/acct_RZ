from __future__ import annotations

from pathlib import Path

import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.features_blacklist import lookup_step1, lookup_step2
from acct_rz.features_org_blacklist import lookup_step3
from acct_rz.features_windows import lookup_step4
from acct_rz.keys import build_history_query_snapshot
from acct_rz.product_blacklist_features import build_blacklist_features


def run_demo_pipeline(input_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    history_df = pl.read_csv(input_path)
    query_snapshot = build_history_query_snapshot(history_df)
    event_fact = build_default_event_key_fact(history_df)
    blacklist_features = build_blacklist_features(history_df, query_snapshot)

    step1 = lookup_step1(query_snapshot, event_fact)
    step2 = lookup_step2(query_snapshot, event_fact)
    step3 = lookup_step3(query_snapshot, event_fact)
    step4 = lookup_step4(query_snapshot, event_fact)

    blacklist_features.write_parquet(out_dir / "blacklist_features.parquet")
    step1.write_parquet(out_dir / "step1_blacklist.parquet")
    step2.write_parquet(out_dir / "step2_traceback.parquet")
    step3.write_parquet(out_dir / "step3_org_blacklist.parquet")
    step4.write_parquet(out_dir / "step4_window_counts.parquet")
