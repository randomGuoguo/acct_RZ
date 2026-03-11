import polars as pl

from acct_rz.agg_recency import add_days_since_columns


def test_add_days_since_columns_uses_app_dt_as_reference() -> None:
    df = pl.DataFrame(
        {
            "app_dt": [20250101],
            "latest_default_dt": [20241201],
            "first_default_dt": [20240101],
        }
    )

    result = add_days_since_columns(
        df,
        {
            "latest_default_dt": "days_since_latest_default",
            "first_default_dt": "days_since_first_default",
        },
    )

    assert result["days_since_latest_default"].item() > 0
    assert result["days_since_first_default"].item() > result["days_since_latest_default"].item()
