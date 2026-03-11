from __future__ import annotations

import polars as pl


def _as_date_expr(name: str) -> pl.Expr:
    text = pl.col(name).cast(pl.Utf8, strict=False).str.strip_chars()
    return pl.coalesce(
        [
            text.str.strptime(pl.Date, "%Y%m%d", strict=False),
            text.str.strptime(pl.Date, "%Y-%m-%d", strict=False),
            pl.when(pl.col(name).cast(pl.Date, strict=False).is_not_null())
            .then(pl.col(name).cast(pl.Date, strict=False))
            .otherwise(pl.lit(None, dtype=pl.Date)),
        ]
    )


def add_days_since_columns(df: pl.DataFrame, mapping: dict[str, str]) -> pl.DataFrame:
    app_dt = _as_date_expr("app_dt")
    expressions = []
    for source_column, target_column in mapping.items():
        source_dt = _as_date_expr(source_column)
        expressions.append(
            pl.when(source_dt.is_null())
            .then(pl.lit(None, dtype=pl.Int64))
            .otherwise((app_dt - source_dt).dt.total_days())
            .alias(target_column)
        )
    return df.with_columns(expressions)
