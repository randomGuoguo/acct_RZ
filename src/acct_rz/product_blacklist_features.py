from __future__ import annotations

import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.feature_product import BASE_FEATURE_KEY_COLUMNS
from acct_rz.labels_complexity import build_complexity_labels
from acct_rz.labels_history import build_history_labels
from acct_rz.labels_orgtype import build_orgtype_labels
from acct_rz.labels_perftype import build_perftype_labels
from acct_rz.labels_window import build_window_labels


def _join_feature_family(base: pl.DataFrame, family: pl.DataFrame) -> pl.DataFrame:
    key_columns = list(BASE_FEATURE_KEY_COLUMNS)
    duplicate_columns = sorted((set(base.columns) & set(family.columns)) - set(key_columns))
    if duplicate_columns:
        raise ValueError(f"Duplicate feature columns detected: {duplicate_columns}")
    result = base.join(family, on=key_columns, how="left", nulls_equal=True)
    if result.height != base.height:
        raise ValueError("Feature product join changed row cardinality.")
    return result


def build_blacklist_features(history_df: pl.DataFrame, query_snapshot: pl.DataFrame) -> pl.DataFrame:
    event_fact = build_default_event_key_fact(history_df)
    result = query_snapshot.select(list(BASE_FEATURE_KEY_COLUMNS))
    families = [
        build_history_labels(query_snapshot, event_fact),
        build_window_labels(query_snapshot, event_fact),
        build_orgtype_labels(query_snapshot, event_fact),
        build_perftype_labels(query_snapshot, event_fact),
        build_complexity_labels(query_snapshot, event_fact),
    ]
    for family in families:
        result = _join_feature_family(result, family)
    return result.sort(*BASE_FEATURE_KEY_COLUMNS)
