from __future__ import annotations

import polars as pl

from acct_rz.keys import BASE_KEY_COLUMNS, build_history_query_snapshot
from acct_rz.lookup_base import format_final_date_columns, resolve_query_snapshot_and_event_fact, with_matched_event_dt


def _lookup_blacklist_features(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    events = event_fact.select("key_type", "key_value", "event_dt")
    matched = with_matched_event_dt(query_snapshot.join(events, on=["key_type", "key_value"], how="left"))
    return (
        matched.group_by(BASE_KEY_COLUMNS)
        .agg(
            (pl.col("matched_event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("black_hit_ever"),
            pl.col("matched_event_dt").min().alias("first_default_event_dt"),
            pl.col("matched_event_dt").max().alias("latest_default_event_dt"),
            pl.col("matched_event_dt").is_not_null().sum().alias("hit_event_cnt_asof_dt"),
        )
        .sort(*BASE_KEY_COLUMNS)
    )


def lookup_step1(history_or_query_snapshot: pl.DataFrame, query_snapshot_or_event_fact: pl.DataFrame) -> pl.DataFrame:
    query_snapshot, event_fact = resolve_query_snapshot_and_event_fact(
        history_or_query_snapshot, query_snapshot_or_event_fact
    )
    return format_final_date_columns(
        _lookup_blacklist_features(query_snapshot, event_fact).select(
            "app_dt", "key_type", "key_value", "PID", "ID", "black_hit_ever", "first_default_event_dt"
        )
    )


def lookup_step2(history_or_query_snapshot: pl.DataFrame, query_snapshot_or_event_fact: pl.DataFrame) -> pl.DataFrame:
    query_snapshot, event_fact = resolve_query_snapshot_and_event_fact(
        history_or_query_snapshot, query_snapshot_or_event_fact
    )
    return format_final_date_columns(_lookup_blacklist_features(query_snapshot, event_fact))


def build_blacklist_asof_features(df: pl.DataFrame) -> pl.DataFrame:
    return lookup_step2(df, build_history_query_snapshot(df))


def build_step1_blacklist_product(df: pl.DataFrame) -> pl.DataFrame:
    return lookup_step1(df, build_history_query_snapshot(df))


def build_step2_traceback_product(df: pl.DataFrame) -> pl.DataFrame:
    return lookup_step2(df, build_history_query_snapshot(df))
