from __future__ import annotations

import polars as pl

from acct_rz.feature_product import BASE_FEATURE_KEY_COLUMNS
from acct_rz.keys import build_history_query_snapshot
from acct_rz.labels_orgtype import build_orgtype_labels
from acct_rz.labels_perftype import build_perftype_labels
from acct_rz.labels_window import build_window_labels
from acct_rz.lookup_base import format_final_date_columns, resolve_query_snapshot_and_event_fact


def lookup_step4(history_or_query_snapshot: pl.DataFrame, query_snapshot_or_event_fact: pl.DataFrame) -> pl.DataFrame:
    query_snapshot, event_fact = resolve_query_snapshot_and_event_fact(
        history_or_query_snapshot, query_snapshot_or_event_fact
    )
    result = (
        query_snapshot.select(list(BASE_FEATURE_KEY_COLUMNS))
        .join(
            build_window_labels(query_snapshot, event_fact),
            on=list(BASE_FEATURE_KEY_COLUMNS),
            how="left",
            nulls_equal=True,
        )
        .join(
            build_orgtype_labels(query_snapshot, event_fact),
            on=list(BASE_FEATURE_KEY_COLUMNS),
            how="left",
            nulls_equal=True,
        )
        .join(
            build_perftype_labels(query_snapshot, event_fact),
            on=list(BASE_FEATURE_KEY_COLUMNS),
            how="left",
            nulls_equal=True,
        )
        .select(
            *BASE_FEATURE_KEY_COLUMNS,
            "default_cnt_3m",
            "default_cnt_6m",
            "default_cnt_12m",
            "default_cnt_3m_bank",
            "default_cnt_6m_bank",
            "default_cnt_3m_rate24",
            "default_cnt_3m_fpd",
            "default_cnt_3m_dpd",
        )
        .with_columns(
            pl.col(
                [
                    "default_cnt_3m",
                    "default_cnt_6m",
                    "default_cnt_12m",
                    "default_cnt_3m_bank",
                    "default_cnt_6m_bank",
                    "default_cnt_3m_rate24",
                    "default_cnt_3m_fpd",
                    "default_cnt_3m_dpd",
                ]
            )
            .fill_null(0)
            .cast(pl.UInt32)
        )
        .sort(*BASE_FEATURE_KEY_COLUMNS)
    )
    return format_final_date_columns(result)


def build_window_count_features(df: pl.DataFrame) -> pl.DataFrame:
    return lookup_step4(df, build_history_query_snapshot(df))
