import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_history_labels_returns_model_facing_columns() -> None:
    from acct_rz.labels_history import build_history_labels

    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["2024-01-01"],
            "target": [1],
            "mob": [0],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_history_labels(query_snapshot, event_fact)

    assert {"ever_default_flag", "days_since_latest_default", "default_cnt_lifetime"}.issubset(set(result.columns))
