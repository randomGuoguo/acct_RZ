import polars as pl

from acct_rz.features_blacklist import build_blacklist_asof_features, lookup_step2
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_blacklist_asof_features_tracks_first_and_latest_hits() -> None:
    df = pl.DataFrame(
        {
            "PID": ["p1", "p1", "p1"],
            "ID": ["i1", "i1", "i1"],
            "app_dt": ["20240310", "20241001", "20250101"],
            "target": [1, 0, 0],
            "mob": ["6", "", ""],
            "Org_class_new": ["Bank", "Bank", "Bank"],
            "Org_new": ["A", "A", "A"],
            "perf_type": ["dpd", "dpd", "dpd"],
            "threshold_dpd": ["30", "30", "30"],
            "channel_new": ["api", "api", "api"],
        }
    )

    result = build_blacklist_asof_features(df).filter(pl.col("key_type") == "pid_id").sort("app_dt")

    assert result["black_hit_ever"].to_list() == [0, 1, 1]
    assert result["hit_event_cnt_asof_dt"].to_list() == [0, 1, 1]
    assert result["app_dt"].to_list() == [20240310, 20241001, 20250101]
    assert result["first_default_event_dt"].to_list() == [None, 20240910, 20240910]


def test_lookup_step2_returns_rows_for_arbitrary_query_dates() -> None:
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

    result = lookup_step2(history_df, build_external_query_snapshot(query_df))

    assert result["app_dt"].item() == 20241001
    assert result["black_hit_ever"].item() == 1
    assert result["first_default_event_dt"].item() == 20240701
    assert result["PID"].item() == "p1"
    assert result["ID"].item() == "i1"


def test_lookup_step2_still_matches_compatibility_contract() -> None:
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

    result = lookup_step2(history_df, query_snapshot)

    assert {"black_hit_ever", "latest_default_event_dt", "hit_event_cnt_asof_dt"}.issubset(set(result.columns))
