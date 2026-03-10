from __future__ import annotations

import polars as pl

from acct_rz.keys import BASE_KEY_COLUMNS, build_history_query_snapshot
from acct_rz.lookup_base import format_final_date_columns, with_matched_event_dt
from acct_rz.normalize import build_application_base
from acct_rz.events import build_default_event_key_fact


def lookup_step3(
    history_or_query_snapshot: pl.DataFrame, query_snapshot_or_event_fact: pl.DataFrame, output_format: str = "long"
) -> pl.DataFrame:
    if output_format != "long":
        raise ValueError("Only long output_format is supported.")

    if set(BASE_KEY_COLUMNS).issubset(history_or_query_snapshot.columns) and {
        "event_dt",
        "key_type",
        "key_value",
    }.issubset(query_snapshot_or_event_fact.columns):
        query_snapshot = history_or_query_snapshot
        event_fact = query_snapshot_or_event_fact
        org_classes = (
            event_fact.select(pl.col("Org_class_new").cast(pl.Utf8, strict=False).alias("org_class"))
            .drop_nulls()
            .unique()
            .sort("org_class")
        )
    else:
        history_df = history_or_query_snapshot
        query_snapshot = query_snapshot_or_event_fact
        event_fact = build_default_event_key_fact(history_df)
        org_classes = (
            build_application_base(history_df)
            .select(pl.col("Org_class_new").cast(pl.Utf8, strict=False).alias("org_class"))
            .drop_nulls()
            .unique()
            .sort("org_class")
        )
    query_org = query_snapshot.join(org_classes, how="cross")
    events = event_fact.select(
        "key_type",
        "key_value",
        "event_dt",
        pl.col("Org_class_new").cast(pl.Utf8, strict=False).alias("org_class"),
    )
    matched = with_matched_event_dt(query_org.join(events, on=["key_type", "key_value", "org_class"], how="left"))
    result = (
        matched.group_by([*BASE_KEY_COLUMNS, "org_class"])
        .agg(
            (pl.col("matched_event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("black_hit_ever_by_org_class"),
            pl.col("matched_event_dt").min().alias("first_default_event_dt_by_org_class"),
        )
        .sort(*BASE_KEY_COLUMNS, "org_class")
    )
    return format_final_date_columns(result)


def build_org_class_blacklist_features(df: pl.DataFrame) -> pl.DataFrame:
    return lookup_step3(df, build_history_query_snapshot(df))
