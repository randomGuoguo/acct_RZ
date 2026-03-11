import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_window_labels_exposes_model_window_fields() -> None:
    from acct_rz.labels_window import build_window_labels

    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["2024-10-01"],
            "target": [1],
            "mob": [0],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_window_labels(query_snapshot, event_fact)

    assert {"default_flag_3m", "default_cnt_12m", "default_perf_type_cnt_36m"}.issubset(set(result.columns))
