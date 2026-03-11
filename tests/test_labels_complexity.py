import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_complexity_labels_returns_multi_head_features() -> None:
    from acct_rz.labels_complexity import build_complexity_labels

    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-06-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_complexity_labels(query_snapshot, event_fact)

    assert {"is_multi_org_default_12m", "is_multi_perf_default_12m", "latest_default_org_type"}.issubset(
        set(result.columns)
    )
