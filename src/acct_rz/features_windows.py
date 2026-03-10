from __future__ import annotations

import polars as pl

from acct_rz.keys import BASE_KEY_COLUMNS, build_history_query_snapshot
from acct_rz.lookup_base import format_final_date_columns, resolve_query_snapshot_and_event_fact, with_matched_event_dt


def lookup_step4(history_or_query_snapshot: pl.DataFrame, query_snapshot_or_event_fact: pl.DataFrame) -> pl.DataFrame:
    query_snapshot, event_fact = resolve_query_snapshot_and_event_fact(
        history_or_query_snapshot, query_snapshot_or_event_fact
    )
    events = event_fact.select(
        "key_type",
        "key_value",
        "event_dt",
        pl.col("Org_class_new").cast(pl.Utf8, strict=False).alias("org_class"),
        pl.col("perf_type").cast(pl.Utf8, strict=False).alias("perf_type"),
    )
    joined = with_matched_event_dt(query_snapshot.join(events, on=["key_type", "key_value"], how="left"))
    result = (
        joined.group_by(BASE_KEY_COLUMNS)
        .agg(
            (
                ((pl.col("matched_event_dt").is_not_null()) & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo")))
                .fill_null(False)
                .sum()
            ).alias("default_cnt_3m"),
            (
                ((pl.col("matched_event_dt").is_not_null()) & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-6mo")))
                .fill_null(False)
                .sum()
            ).alias("default_cnt_6m"),
            (
                ((pl.col("matched_event_dt").is_not_null()) & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-12mo")))
                .fill_null(False)
                .sum()
            ).alias("default_cnt_12m"),
            (
                (
                    (pl.col("matched_event_dt").is_not_null())
                    & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                    & (pl.col("org_class") == "Bank")
                )
                .fill_null(False)
                .sum()
            ).alias("default_cnt_3m_bank"),
            (
                (
                    (pl.col("matched_event_dt").is_not_null())
                    & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-6mo"))
                    & (pl.col("org_class") == "Bank")
                )
                .fill_null(False)
                .sum()
            ).alias("default_cnt_6m_bank"),
            (
                (
                    (pl.col("matched_event_dt").is_not_null())
                    & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                    & (pl.col("org_class") == "Rate24")
                )
                .fill_null(False)
                .sum()
            ).alias("default_cnt_3m_rate24"),
            (
                (
                    (pl.col("matched_event_dt").is_not_null())
                    & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                    & (pl.col("perf_type") == "fpd")
                )
                .fill_null(False)
                .sum()
            ).alias("default_cnt_3m_fpd"),
            (
                (
                    (pl.col("matched_event_dt").is_not_null())
                    & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                    & (pl.col("perf_type") == "dpd")
                )
                .fill_null(False)
                .sum()
            ).alias("default_cnt_3m_dpd"),
        )
        .sort(*BASE_KEY_COLUMNS)
    )
    return format_final_date_columns(result)


def build_window_count_features(df: pl.DataFrame) -> pl.DataFrame:
    return lookup_step4(df, build_history_query_snapshot(df))
