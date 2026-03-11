from __future__ import annotations

import polars as pl

from acct_rz.agg_lifetime import build_lifetime_aggregates
from acct_rz.keys import BASE_KEY_COLUMNS, build_history_query_snapshot
from acct_rz.lookup_base import format_final_date_columns, resolve_query_snapshot_and_event_fact


def _lookup_blacklist_features(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    return (
        build_lifetime_aggregates(query_snapshot, event_fact)
        .rename(
            {
                "ever_default_flag": "black_hit_ever",
                "first_default_dt": "first_default_event_dt",
                "latest_default_dt": "latest_default_event_dt",
                "default_cnt_lifetime": "hit_event_cnt_asof_dt",
            }
        )
        .select(
            *BASE_KEY_COLUMNS,
            "black_hit_ever",
            "first_default_event_dt",
            "latest_default_event_dt",
            "hit_event_cnt_asof_dt",
        )
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
