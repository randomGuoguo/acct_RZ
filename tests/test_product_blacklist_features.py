import polars as pl

from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_blacklist_features_returns_one_row_per_query_key() -> None:
    from acct_rz.product_blacklist_features import build_blacklist_features

    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-06-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(
        pl.DataFrame(
            {
                "app_dt": ["2025-01-01", "2025-01-01"],
                "PID": ["p1", "p9"],
            }
        )
    )

    result = build_blacklist_features(history_df, query_snapshot)

    assert result.shape[0] == 2
    assert "ever_default_flag" in result.columns
    assert "default_cnt_12m_bank" in result.columns
