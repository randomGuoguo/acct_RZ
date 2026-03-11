import polars as pl

from acct_rz.query_lookup import lookup_all_steps


def test_lookup_all_steps_returns_dict_of_step_outputs() -> None:
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

    result = lookup_all_steps(history_df, query_df)

    assert set(result.keys()) == {"blacklist_features", "step1", "step2", "step3", "step4"}
    assert "ever_default_flag" in result["blacklist_features"].columns
    assert result["step1"]["app_dt"].item() == 20241001
    assert result["step1"]["first_default_event_dt"].item() == 20240701
    assert result["step1"]["black_hit_ever"].item() == 1
