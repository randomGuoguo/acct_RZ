from __future__ import annotations

import polars as pl


def build_application_base(df: pl.DataFrame) -> pl.DataFrame:
    """构建申请标准层。

    参数:
        df: 原始申请明细，至少包含 `app_dt`、`target`、`mob`。

    返回:
        标准化后的申请表，包含日期化后的 `app_dt`、`mob_filled`、`is_default`、`event_dt`。

    规则:
        仅 `target == 1` 认定为违约；`mob` 缺失或非法时回填为 6。

    示例:
        `20240310 + mob=6` 的违约事件生效日应为 `2024-09-10`。

    实现说明:
        先做轻量类型标准化，再按业务规则生成衍生列并过滤非法日期。
    """

    app_dt_text = pl.col("app_dt").cast(pl.Utf8, strict=False).str.strip_chars()
    app_dt_expr = pl.coalesce(
        [
            app_dt_text.str.strptime(pl.Date, "%Y%m%d", strict=False),
            app_dt_text.str.strptime(pl.Date, "%Y-%m-%d", strict=False),
            pl.when(pl.col("app_dt").cast(pl.Date, strict=False).is_not_null())
            .then(pl.col("app_dt").cast(pl.Date, strict=False))
            .otherwise(pl.lit(None, dtype=pl.Date)),
        ]
    )
    mob_text = pl.col("mob").cast(pl.Utf8, strict=False).str.strip_chars()
    mob_filled = (
        pl.when(mob_text.is_null() | (mob_text == ""))
        .then(pl.lit(6))
        .otherwise(mob_text.cast(pl.Int64, strict=False))
        .fill_null(6)
        .alias("mob_filled")
    )
    is_default = (
        pl.when(pl.col("target").cast(pl.Float64, strict=False) == 1.0)
        .then(pl.lit(1))
        .otherwise(pl.lit(0))
        .cast(pl.Int8)
        .alias("is_default")
    )

    base = (
        df.with_columns(
            pl.col("PID").cast(pl.Utf8, strict=False),
            pl.col("ID").cast(pl.Utf8, strict=False),
            app_dt_expr.alias("app_dt"),
            mob_filled,
            is_default,
        )
        .with_columns(
            pl.when(pl.col("is_default") == 1)
            .then(pl.col("app_dt").dt.offset_by(pl.format("{}mo", pl.col("mob_filled"))))
            .otherwise(pl.lit(None, dtype=pl.Date))
            .alias("event_dt")
        )
        .filter(pl.col("app_dt").is_not_null())
    )
    return base
