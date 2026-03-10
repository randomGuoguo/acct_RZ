import polars as pl

from acct_rz.keys import build_selected_key_snapshot, expand_all_key_types


def test_build_selected_key_snapshot_keeps_split_key_columns() -> None:
    df = pl.DataFrame(
        {
            "PID": ["p1", None, "p3"],
            "ID": ["i1", "i2", None],
            "app_dt": ["20240101", "20240102", "20240103"],
        }
    )

    result = build_selected_key_snapshot(df)

    assert result.select("key_type").to_series().to_list() == ["pid_id", "id", "pid"]
    assert result.select("PID").to_series().to_list() == ["p1", None, "p3"]
    assert result.select("ID").to_series().to_list() == ["i1", "i2", None]


def test_expand_all_key_types_nulls_irrelevant_split_columns() -> None:
    df = pl.DataFrame({"PID": ["p1"], "ID": ["i1"], "app_dt": ["20240101"]})

    result = expand_all_key_types(df).sort("key_type")

    assert result["key_type"].to_list() == ["id", "pid", "pid_id"]
    assert result["PID"].to_list() == [None, "p1", "p1"]
    assert result["ID"].to_list() == ["i1", None, "i1"]
