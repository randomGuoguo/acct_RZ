import polars as pl

from acct_rz.events import build_default_event_key_fact


def test_build_default_event_key_fact_expands_only_legal_keys() -> None:
    df = pl.DataFrame(
        {
            "PID": ["p1", None],
            "ID": ["i1", "i2"],
            "app_dt": ["20240310", "20240310"],
            "target": [1, 1],
            "mob": ["6", ""],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
            "threshold_dpd": ["30", "60"],
            "channel_new": ["api", "h5"],
        }
    )

    result = build_default_event_key_fact(df)
    pairs = set(zip(result["key_type"].to_list(), result["key_value"].to_list()))

    assert ("pid_id", "p1|i1") in pairs
    assert ("id", "i1") in pairs
    assert ("pid", "p1") in pairs
    assert ("pid_id", "None|i2") not in pairs
    assert ("id", "i2") in pairs
