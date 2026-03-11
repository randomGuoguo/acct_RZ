import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_window_aggregates_returns_multi_window_counts() -> None:
    from acct_rz.agg_windows import build_window_aggregates

    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-10-01", "2024-12-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_window_aggregates(query_snapshot, event_fact)

    assert result["default_cnt_3m"].item() >= 1
    assert result["default_cnt_12m"].item() == 2
