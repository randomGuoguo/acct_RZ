from __future__ import annotations

import polars as pl

from acct_rz.agg_breakdown import build_grouped_breakdown
from acct_rz.agg_recency import add_days_since_columns
from acct_rz.feature_product import BASE_FEATURE_KEY_COLUMNS, BLACKLIST_WINDOWS, STABLE_ORG_TYPES, STABLE_PERF_TYPES


def _build_stable_breakdown_labels(
    query_snapshot: pl.DataFrame,
    event_fact: pl.DataFrame,
    *,
    dimension: str,
    stable_values: tuple[str, ...],
) -> pl.DataFrame:
    breakdown = build_grouped_breakdown(query_snapshot, event_fact, dimension=dimension, dim_values=stable_values)
    result = query_snapshot.select(list(BASE_FEATURE_KEY_COLUMNS))
    for dim_value in stable_values:
        rename_map = {"latest_default_dt": f"latest_default_dt_{dim_value}"}
        for window in BLACKLIST_WINDOWS:
            rename_map[f"default_flag_{window}"] = f"default_flag_{window}_{dim_value}"
            rename_map[f"default_cnt_{window}"] = f"default_cnt_{window}_{dim_value}"
        frame = (
            breakdown.filter(pl.col("dim_value") == dim_value)
            .drop("dim_type", "dim_value", "ever_default_flag", "default_cnt_lifetime", "default_month_cnt_lifetime")
            .drop("first_default_dt", *[f"default_month_cnt_{window}" for window in BLACKLIST_WINDOWS])
            .rename(rename_map)
        )
        frame = add_days_since_columns(
            frame,
            {f"latest_default_dt_{dim_value}": f"days_since_latest_default_{dim_value}"},
        ).drop(f"latest_default_dt_{dim_value}")
        result = result.join(frame, on=list(BASE_FEATURE_KEY_COLUMNS), how="left", nulls_equal=True)
    return result.sort(*BASE_FEATURE_KEY_COLUMNS)


def build_orgtype_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    return _build_stable_breakdown_labels(
        query_snapshot,
        event_fact,
        dimension="org_type",
        stable_values=STABLE_ORG_TYPES,
    )


def build_perftype_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    return _build_stable_breakdown_labels(
        query_snapshot,
        event_fact,
        dimension="perf_type",
        stable_values=STABLE_PERF_TYPES,
    )
