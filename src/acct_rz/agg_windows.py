from __future__ import annotations

import polars as pl

from acct_rz.feature_product import (
    BASE_FEATURE_KEY_COLUMNS,
    BLACKLIST_WINDOWS,
    normalize_org_type_expr,
    normalize_perf_type_expr,
    window_token_to_offset,
)
from acct_rz.lookup_base import with_matched_event_dt


def build_window_aggregates(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    events = event_fact.select(
        "key_type",
        "key_value",
        "event_dt",
        normalize_org_type_expr(),
        normalize_perf_type_expr(),
    )
    joined = with_matched_event_dt(query_snapshot.join(events, on=["key_type", "key_value"], how="left"))
    month_bucket = pl.col("matched_event_dt").dt.strftime("%Y-%m")
    aggregations: list[pl.Expr] = []
    for window in BLACKLIST_WINDOWS:
        in_window = (
            pl.col("matched_event_dt").is_not_null()
            & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by(window_token_to_offset(window)))
        ).fill_null(False)
        aggregations.extend(
            [
                (in_window.sum() > 0).cast(pl.Int8).alias(f"default_flag_{window}"),
                in_window.sum().alias(f"default_cnt_{window}"),
                pl.when(in_window).then(month_bucket).otherwise(None).drop_nulls().n_unique().alias(
                    f"default_month_cnt_{window}"
                ),
                pl.when(in_window).then(pl.col("org_type")).otherwise(None).drop_nulls().n_unique().alias(
                    f"default_org_type_cnt_{window}"
                ),
                pl.when(in_window).then(pl.col("perf_type")).otherwise(None).drop_nulls().n_unique().alias(
                    f"default_perf_type_cnt_{window}"
                ),
            ]
        )
    return joined.group_by(list(BASE_FEATURE_KEY_COLUMNS)).agg(aggregations).sort(*BASE_FEATURE_KEY_COLUMNS)
