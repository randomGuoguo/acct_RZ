from __future__ import annotations

import polars as pl

from acct_rz.agg_breakdown import build_grouped_breakdown
from acct_rz.feature_product import BASE_FEATURE_KEY_COLUMNS, BLACKLIST_WINDOWS


def _latest_dim_value(breakdown: pl.DataFrame, target_column: str) -> pl.DataFrame:
    if breakdown.is_empty():
        return breakdown.select([*BASE_FEATURE_KEY_COLUMNS]).unique().with_columns(
            pl.lit(None, dtype=pl.Utf8).alias(target_column)
        )
    return (
        breakdown.filter(pl.col("latest_default_dt").is_not_null())
        .sort(
            [*BASE_FEATURE_KEY_COLUMNS, "latest_default_dt", "dim_value"],
            descending=[False, False, False, False, False, True, False],
        )
        .unique(subset=list(BASE_FEATURE_KEY_COLUMNS), keep="first")
        .select([*BASE_FEATURE_KEY_COLUMNS, pl.col("dim_value").alias(target_column)])
    )


def _multi_hit_flags(breakdown: pl.DataFrame, prefix: str) -> pl.DataFrame:
    expressions: list[pl.Expr] = []
    for window in BLACKLIST_WINDOWS:
        expressions.append(
            (pl.col(f"default_flag_{window}").sum() > 1).cast(pl.Int8).alias(f"is_multi_{prefix}_default_{window}")
        )
    return breakdown.group_by(list(BASE_FEATURE_KEY_COLUMNS)).agg(expressions)


def build_complexity_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    org_breakdown = build_grouped_breakdown(query_snapshot, event_fact, dimension="org_type")
    perf_breakdown = build_grouped_breakdown(query_snapshot, event_fact, dimension="perf_type")
    result = query_snapshot.select(list(BASE_FEATURE_KEY_COLUMNS))
    result = result.join(_multi_hit_flags(org_breakdown, "org"), on=list(BASE_FEATURE_KEY_COLUMNS), how="left")
    result = result.join(_multi_hit_flags(perf_breakdown, "perf"), on=list(BASE_FEATURE_KEY_COLUMNS), how="left")
    result = result.join(
        _latest_dim_value(org_breakdown, "latest_default_org_type"),
        on=list(BASE_FEATURE_KEY_COLUMNS),
        how="left",
    )
    result = result.join(
        _latest_dim_value(perf_breakdown, "latest_default_perf_type"),
        on=list(BASE_FEATURE_KEY_COLUMNS),
        how="left",
    )
    fill_columns = [name for name in result.columns if name.startswith("is_multi_")]
    if fill_columns:
        result = result.with_columns(pl.col(fill_columns).fill_null(0).cast(pl.Int8))
    return result.sort(*BASE_FEATURE_KEY_COLUMNS)
