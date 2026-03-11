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


def _dimension_expr(dimension: str) -> pl.Expr:
    if dimension == "org_type":
        return normalize_org_type_expr(alias="dim_value")
    if dimension == "perf_type":
        return normalize_perf_type_expr(alias="dim_value")
    raise ValueError(f"Unsupported dimension: {dimension}")


def build_grouped_breakdown(
    query_snapshot: pl.DataFrame,
    event_fact: pl.DataFrame,
    dimension: str,
    dim_values: tuple[str, ...] | list[str] | None = None,
) -> pl.DataFrame:
    dim_expr = _dimension_expr(dimension)
    if dim_values is None:
        dim_frame = event_fact.select(dim_expr).drop_nulls().unique().sort("dim_value")
    else:
        dim_frame = pl.DataFrame({"dim_value": list(dim_values)})
    if dim_frame.height == 0:
        return query_snapshot.clear().with_columns(
            pl.lit(dimension, dtype=pl.Utf8).alias("dim_type"),
            pl.lit(None, dtype=pl.Utf8).alias("dim_value"),
        )

    query_dim = query_snapshot.join(
        dim_frame.with_columns(pl.lit(dimension, dtype=pl.Utf8).alias("dim_type")),
        how="cross",
    )
    events = event_fact.select("key_type", "key_value", "event_dt", dim_expr)
    joined = with_matched_event_dt(query_dim.join(events, on=["key_type", "key_value", "dim_value"], how="left"))
    month_bucket = pl.col("matched_event_dt").dt.strftime("%Y-%m")
    aggregations: list[pl.Expr] = [
        (pl.col("matched_event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("ever_default_flag"),
        pl.col("matched_event_dt").is_not_null().sum().alias("default_cnt_lifetime"),
        month_bucket.drop_nulls().n_unique().alias("default_month_cnt_lifetime"),
        pl.col("matched_event_dt").min().alias("first_default_dt"),
        pl.col("matched_event_dt").max().alias("latest_default_dt"),
    ]
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
            ]
        )
    return (
        joined.group_by([*BASE_FEATURE_KEY_COLUMNS, "dim_type", "dim_value"])
        .agg(aggregations)
        .sort(*BASE_FEATURE_KEY_COLUMNS, "dim_type", "dim_value")
    )
