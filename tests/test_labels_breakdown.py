import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_breakdown_labels_expand_only_stable_categories() -> None:
    from acct_rz.labels_orgtype import build_orgtype_labels
    from acct_rz.labels_perftype import build_perftype_labels

    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-02-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    org_df = build_orgtype_labels(query_snapshot, event_fact)
    perf_df = build_perftype_labels(query_snapshot, event_fact)

    assert "default_cnt_12m_bank" in org_df.columns
    assert "default_cnt_12m_rate24" in org_df.columns
    assert "default_cnt_12m_dpd" in perf_df.columns
    assert "default_cnt_12m_fpd" in perf_df.columns
