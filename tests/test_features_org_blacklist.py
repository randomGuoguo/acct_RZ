import polars as pl

from acct_rz.features_org_blacklist import build_org_class_blacklist_features, lookup_step3
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_org_class_blacklist_features_keeps_org_class_separate() -> None:
    df = pl.DataFrame(
        {
            "PID": ["p1", "p1", "p1"],
            "ID": ["i1", "i1", "i1"],
            "app_dt": ["20240310", "20241001", "20241001"],
            "target": [1, 0, 0],
            "mob": ["6", "", ""],
            "Org_class_new": ["Bank", "Bank", "Rate24"],
            "Org_new": ["A", "A", "B"],
            "perf_type": ["dpd", "dpd", "dpd"],
            "threshold_dpd": ["30", "30", "30"],
            "channel_new": ["api", "api", "api"],
        }
    )

    result = build_org_class_blacklist_features(df).filter(pl.col("key_type") == "pid_id")
    bank_hit = result.filter(pl.col("org_class") == "Bank")["black_hit_ever_by_org_class"].max()
    rate24_hit = result.filter(pl.col("org_class") == "Rate24")["black_hit_ever_by_org_class"].max()

    assert bank_hit == 1
    assert rate24_hit == 0


def test_lookup_step3_returns_long_form_org_rows_for_arbitrary_queries() -> None:
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["20240101"],
            "target": [1],
            "mob": ["6"],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
            "threshold_dpd": ["30"],
            "channel_new": ["api"],
        }
    )
    query_df = pl.DataFrame({"app_dt": ["20241001"], "PID": ["p1"], "ID": ["i1"]})

    result = lookup_step3(history_df, build_external_query_snapshot(query_df))

    assert {"PID", "ID", "org_class", "black_hit_ever_by_org_class"}.issubset(set(result.columns))
    assert result["app_dt"].item() == 20241001
    assert result["first_default_event_dt_by_org_class"].item() == 20240701
    assert result.filter(pl.col("org_class") == "Bank")["black_hit_ever_by_org_class"].item() == 1
