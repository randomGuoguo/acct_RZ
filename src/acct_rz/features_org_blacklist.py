from __future__ import annotations

import polars as pl

from acct_rz.agg_breakdown import build_grouped_breakdown
from acct_rz.events import build_default_event_key_fact
from acct_rz.feature_product import normalize_org_type_expr
from acct_rz.keys import BASE_KEY_COLUMNS, build_history_query_snapshot
from acct_rz.lookup_base import format_final_date_columns
from acct_rz.normalize import build_application_base


def _compat_org_class_expr() -> pl.Expr:
    return (
        pl.when(pl.col("dim_value") == "bank")
        .then(pl.lit("Bank"))
        .when(pl.col("dim_value") == "rate24")
        .then(pl.lit("Rate24"))
        .when(pl.col("dim_value") == "rate36")
        .then(pl.lit("Rate36"))
        .otherwise(pl.col("dim_value").str.to_titlecase())
        .alias("org_class")
    )


def lookup_step3(
    history_or_query_snapshot: pl.DataFrame, query_snapshot_or_event_fact: pl.DataFrame, output_format: str = "long"
) -> pl.DataFrame:
    if output_format != "long":
        raise ValueError("Only long output_format is supported.")
    dim_values: list[str] | None = None
    if set(BASE_KEY_COLUMNS).issubset(history_or_query_snapshot.columns) and {
        "event_dt",
        "key_type",
        "key_value",
    }.issubset(query_snapshot_or_event_fact.columns):
        query_snapshot = history_or_query_snapshot
        event_fact = query_snapshot_or_event_fact
    else:
        history_df = history_or_query_snapshot
        query_snapshot = query_snapshot_or_event_fact
        event_fact = build_default_event_key_fact(history_df)
        dim_values = (
            build_application_base(history_df)
            .select(normalize_org_type_expr(alias="dim_value"))
            .drop_nulls()
            .unique()
            .sort("dim_value")["dim_value"]
            .to_list()
        )
    result = (
        build_grouped_breakdown(query_snapshot, event_fact, dimension="org_type", dim_values=dim_values)
        .with_columns(_compat_org_class_expr())
        .select(
            *BASE_KEY_COLUMNS,
            "org_class",
            pl.col("ever_default_flag").alias("black_hit_ever_by_org_class"),
            pl.col("first_default_dt").alias("first_default_event_dt_by_org_class"),
        )
        .sort(*BASE_KEY_COLUMNS, "org_class")
    )
    return format_final_date_columns(result)


def build_org_class_blacklist_features(df: pl.DataFrame) -> pl.DataFrame:
    return lookup_step3(df, build_history_query_snapshot(df))
