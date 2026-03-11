from __future__ import annotations

import polars as pl

from acct_rz.feature_product import BASE_FEATURE_KEY_COLUMNS
from acct_rz.lookup_base import with_matched_event_dt


def build_lifetime_aggregates(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    events = event_fact.select("key_type", "key_value", "event_dt")
    matched = with_matched_event_dt(query_snapshot.join(events, on=["key_type", "key_value"], how="left"))
    month_bucket = pl.col("matched_event_dt").dt.strftime("%Y-%m")
    return (
        matched.group_by(list(BASE_FEATURE_KEY_COLUMNS))
        .agg(
            (pl.col("matched_event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("ever_default_flag"),
            pl.col("matched_event_dt").min().alias("first_default_dt"),
            pl.col("matched_event_dt").max().alias("latest_default_dt"),
            pl.col("matched_event_dt").is_not_null().sum().alias("default_cnt_lifetime"),
            month_bucket.drop_nulls().n_unique().alias("default_month_cnt_lifetime"),
        )
        .sort(*BASE_FEATURE_KEY_COLUMNS)
    )
