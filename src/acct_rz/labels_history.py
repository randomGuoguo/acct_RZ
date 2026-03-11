from __future__ import annotations

import polars as pl

from acct_rz.agg_lifetime import build_lifetime_aggregates
from acct_rz.agg_recency import add_days_since_columns


def build_history_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    lifetime = build_lifetime_aggregates(query_snapshot, event_fact)
    return add_days_since_columns(
        lifetime,
        {
            "first_default_dt": "days_since_first_default",
            "latest_default_dt": "days_since_latest_default",
        },
    )
