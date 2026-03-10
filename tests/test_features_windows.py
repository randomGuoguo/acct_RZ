import polars as pl

from acct_rz.features_windows import build_window_count_features, lookup_step4
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_window_count_features_uses_event_date_boundaries() -> None:
    df = pl.DataFrame(
        {
            "PID": ["p1", "p1", "p1", "p1"],
            "ID": ["i1", "i1", "i1", "i1"],
            "app_dt": ["20240101", "20240501", "20240701", "20241015"],
            "target": [1, 1, 0, 0],
            "mob": ["3", "3", "", ""],
            "Org_class_new": ["Bank", "Rate24", "Bank", "Bank"],
            "Org_new": ["A", "B", "A", "A"],
            "perf_type": ["dpd", "fpd", "dpd", "dpd"],
            "threshold_dpd": ["30", "30", "30", "30"],
            "channel_new": ["api", "api", "api", "api"],
        }
    )

    result = build_window_count_features(df).filter(
        (pl.col("key_type") == "pid_id") & (pl.col("app_dt") == 20241015)
    )

    assert result["default_cnt_3m"].item() == 1
    assert result["default_cnt_12m"].item() == 2


def test_lookup_step4_returns_zero_rows_for_unseen_keys() -> None:
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
    query_df = pl.DataFrame({"app_dt": ["20241001"], "PID": ["p9"]})

    result = lookup_step4(history_df, build_external_query_snapshot(query_df))

    assert result["app_dt"].item() == 20241001
    assert result["default_cnt_3m"].item() == 0
    assert result["default_cnt_12m"].item() == 0
    assert result["PID"].item() == "p9"
