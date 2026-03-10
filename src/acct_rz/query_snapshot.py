from __future__ import annotations

import polars as pl

from acct_rz.keys import BASE_KEY_COLUMNS, VALID_KEY_TYPES, build_selected_key_snapshot


def _parse_app_dt_expr(name: str = "app_dt") -> pl.Expr:
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


def build_external_query_snapshot(query_df: pl.DataFrame) -> pl.DataFrame:
    if "app_dt" not in query_df.columns:
        raise ValueError("Query input must include app_dt.")

    prepared = query_df.with_columns(_parse_app_dt_expr().alias("app_dt"))
    if "PID" not in prepared.columns:
        prepared = prepared.with_columns(pl.lit(None, dtype=pl.Utf8).alias("PID"))
    if "ID" not in prepared.columns:
        prepared = prepared.with_columns(pl.lit(None, dtype=pl.Utf8).alias("ID"))
    if "key_type" not in prepared.columns:
        prepared = prepared.with_columns(pl.lit(None, dtype=pl.Utf8).alias("key_type"))

    snapshot = build_selected_key_snapshot(prepared)

    if prepared["app_dt"].is_null().any():
        raise ValueError("Query input contains unparseable app_dt values.")
    if prepared.select(pl.col("key_type").drop_nulls().is_in(VALID_KEY_TYPES).all()).item() is False:
        raise ValueError("Query input contains unsupported key_type values.")
    if snapshot.height != prepared.height:
        raise ValueError("Each query row must include a valid PID/ID combination for its key_type.")

    return snapshot.with_columns(pl.col("app_dt").cast(pl.Date)).select(BASE_KEY_COLUMNS)
