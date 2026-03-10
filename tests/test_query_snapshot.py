import polars as pl
import pytest

from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_external_query_snapshot_infers_key_type() -> None:
    query_df = pl.DataFrame(
        {
            "app_dt": ["20250101", "20250102", "20250103"],
            "PID": ["p1", None, "p3"],
            "ID": ["i1", "i2", None],
        }
    )

    result = build_external_query_snapshot(query_df)

    assert result["key_type"].to_list() == ["pid_id", "id", "pid"]


def test_build_external_query_snapshot_rejects_invalid_key_rows() -> None:
    query_df = pl.DataFrame({"app_dt": ["20250101"], "PID": [None], "ID": [None]})

    with pytest.raises(ValueError):
        build_external_query_snapshot(query_df)


def test_build_external_query_snapshot_honors_explicit_key_type() -> None:
    query_df = pl.DataFrame({"app_dt": ["20250101"], "PID": ["p1"], "ID": ["i1"], "key_type": ["pid"]})

    result = build_external_query_snapshot(query_df)

    assert result["key_type"].item() == "pid"
    assert result["PID"].item() == "p1"
    assert result["ID"].item() is None


def test_build_external_query_snapshot_parses_numeric_yyyymmdd() -> None:
    query_df = pl.DataFrame({"app_dt": [20251006], "PID": ["10000279"], "key_type": ["pid"]})

    result = build_external_query_snapshot(query_df)

    assert result["app_dt"].dt.strftime("%Y-%m-%d").item() == "2025-10-06"
