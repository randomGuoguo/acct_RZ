from __future__ import annotations

import polars as pl

from acct_rz.normalize import build_application_base


def _clean_key_expr(name: str) -> pl.Expr:
    value = pl.col(name).cast(pl.Utf8, strict=False).str.strip_chars()
    return pl.when(value == "").then(pl.lit(None, dtype=pl.Utf8)).otherwise(value)


def expand_keys(df: pl.DataFrame) -> pl.DataFrame:
    """展开三种主键口径。

    参数:
        df: 已标准化或兼容标准化字段的数据表。

    返回:
        增加 `key_type`、`key_value` 的长表。

    规则:
        `pid_id` 需要 `PID` 和 `ID` 同时非空；`pid`、`id` 各自只要求对应字段非空。

    示例:
        `PID=p1, ID=i1` 会展开成 `pid_id=p1|i1`、`pid=p1`、`id=i1`。

    实现说明:
        通过三段过滤后的长表拼接，避免三套下游逻辑。
    """

    prepared = df.with_columns(
        _clean_key_expr("PID").alias("PID_clean"),
        _clean_key_expr("ID").alias("ID_clean"),
    )
    pid_id = prepared.filter(pl.col("PID_clean").is_not_null() & pl.col("ID_clean").is_not_null()).with_columns(
        pl.lit("pid_id").alias("key_type"),
        pl.concat_str(["PID_clean", "ID_clean"], separator="|").alias("key_value"),
    )
    id_only = prepared.filter(pl.col("ID_clean").is_not_null()).with_columns(
        pl.lit("id").alias("key_type"),
        pl.col("ID_clean").alias("key_value"),
    )
    pid_only = prepared.filter(pl.col("PID_clean").is_not_null()).with_columns(
        pl.lit("pid").alias("key_type"),
        pl.col("PID_clean").alias("key_value"),
    )
    return pl.concat([pid_id, id_only, pid_only], how="diagonal_relaxed").drop("PID_clean", "ID_clean")


def build_application_key_snapshot(df: pl.DataFrame) -> pl.DataFrame:
    """构建申请日快照键表。

    参数:
        df: 原始申请明细。

    返回:
        唯一化后的申请键快照，粒度为 `app_dt + key_type + key_value`。

    规则:
        同一申请日同一键只保留一行，避免下游连接时重复放大计数。

    示例:
        同一天同一 `pid_id` 多次出现时，只保留一个快照键。

    实现说明:
        先走标准化和键展开，再按快照粒度去重。
    """

    base = build_application_base(df)
    return expand_keys(base).select("app_dt", "key_type", "key_value").unique().sort("app_dt", "key_type", "key_value")
