import polars as pl

from acct_rz.normalize import build_application_base


def test_build_application_base_applies_default_rules() -> None:
    df = pl.DataFrame(
        {
            "PID": ["p1", "p2", "p3"],
            "ID": ["i1", "i2", "i3"],
            "app_dt": ["20240310", "20240310", "20240310"],
            "target": [1, 0, -2],
            "mob": ["6", "", "9"],
            "Org_class_new": ["Bank", "Bank", "Rate24"],
            "Org_new": ["A", "B", "C"],
            "perf_type": ["dpd", "fpd", "dpd"],
            "threshold_dpd": ["30", "30", "60"],
            "channel_new": ["api", "api", "h5"],
        }
    )

    result = build_application_base(df)

    assert result["mob_filled"].to_list() == [6, 6, 9]
    assert result["is_default"].to_list() == [1, 0, 0]
    assert result["event_dt"].dt.strftime("%Y-%m-%d").to_list() == ["2024-09-10", None, None]
