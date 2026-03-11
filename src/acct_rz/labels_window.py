from __future__ import annotations

import polars as pl

from acct_rz.agg_windows import build_window_aggregates


def build_window_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    return build_window_aggregates(query_snapshot, event_fact)
