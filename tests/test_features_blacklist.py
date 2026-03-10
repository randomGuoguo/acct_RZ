import polars as pl

from acct_rz.features_blacklist import build_blacklist_asof_features


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
    assert result["first_default_event_dt"].dt.strftime("%Y-%m-%d").to_list() == [None, "2024-09-10", "2024-09-10"]
