from __future__ import annotations

import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.keys import BASE_KEY_COLUMNS


def with_matched_event_dt(joined: pl.DataFrame) -> pl.DataFrame:
    return joined.with_columns(
        pl.when(pl.col("event_dt").is_not_null() & (pl.col("event_dt") <= pl.col("app_dt")))
        .then(pl.col("event_dt"))
        .otherwise(pl.lit(None, dtype=pl.Date))
        .alias("matched_event_dt")
    )


def resolve_query_snapshot_and_event_fact(
    history_or_query_snapshot: pl.DataFrame, query_snapshot_or_event_fact: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    if set(BASE_KEY_COLUMNS).issubset(history_or_query_snapshot.columns) and {
        "event_dt",
        "key_type",
        "key_value",
    }.issubset(query_snapshot_or_event_fact.columns):
        return history_or_query_snapshot, query_snapshot_or_event_fact
    return query_snapshot_or_event_fact, build_default_event_key_fact(history_or_query_snapshot)


def format_final_date_columns(df: pl.DataFrame) -> pl.DataFrame:
    date_columns = [name for name, dtype in df.schema.items() if dtype == pl.Date]
    if not date_columns:
        return df
    return df.with_columns(pl.col(name).dt.strftime("%Y%m%d").cast(pl.Int64, strict=False).alias(name) for name in date_columns)
