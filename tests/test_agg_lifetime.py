import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_lifetime_aggregates_returns_history_metrics() -> None:
    from acct_rz.agg_lifetime import build_lifetime_aggregates

    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-06-01"],
            "target": [1, 1],
            "mob": [3, 6],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_lifetime_aggregates(query_snapshot, event_fact)

    assert result["ever_default_flag"].item() == 1
    assert result["default_cnt_lifetime"].item() == 2
