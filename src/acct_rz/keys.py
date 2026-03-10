from __future__ import annotations

import polars as pl

from acct_rz.normalize import build_application_base

BASE_KEY_COLUMNS = ["app_dt", "key_type", "key_value", "PID", "ID"]
VALID_KEY_TYPES = ("pid_id", "id", "pid")


def _clean_key_expr(name: str) -> pl.Expr:
    value = pl.col(name).cast(pl.Utf8, strict=False).str.strip_chars()
    return pl.when(value == "").then(pl.lit(None, dtype=pl.Utf8)).otherwise(value)


def _normalize_key_type_expr() -> pl.Expr:
    value = pl.col("key_type").cast(pl.Utf8, strict=False).str.strip_chars().str.to_lowercase()
    return pl.when(value == "").then(pl.lit(None, dtype=pl.Utf8)).otherwise(value)


def _with_clean_keys(df: pl.DataFrame) -> pl.DataFrame:
    prepared = df
    if "PID" not in prepared.columns:
        prepared = prepared.with_columns(pl.lit(None, dtype=pl.Utf8).alias("PID"))
    if "ID" not in prepared.columns:
        prepared = prepared.with_columns(pl.lit(None, dtype=pl.Utf8).alias("ID"))
    if "key_type" not in prepared.columns:
        prepared = prepared.with_columns(pl.lit(None, dtype=pl.Utf8).alias("key_type"))
    return prepared.with_columns(
        _clean_key_expr("PID").alias("PID"),
        _clean_key_expr("ID").alias("ID"),
        _normalize_key_type_expr().alias("key_type"),
    )


def _selected_key_frame(prepared: pl.DataFrame, key_type: str) -> pl.DataFrame:
    if key_type == "pid_id":
        return prepared.filter(
            (pl.col("key_type") == "pid_id") & pl.col("PID").is_not_null() & pl.col("ID").is_not_null()
        ).with_columns(pl.concat_str(["PID", "ID"], separator="|").alias("key_value"))
    if key_type == "id":
        return prepared.filter((pl.col("key_type") == "id") & pl.col("ID").is_not_null()).with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("PID"),
            pl.col("ID").alias("key_value"),
        )
    if key_type == "pid":
        return prepared.filter((pl.col("key_type") == "pid") & pl.col("PID").is_not_null()).with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("ID"),
            pl.col("PID").alias("key_value"),
        )
    raise ValueError(f"Unsupported key_type: {key_type}")


def expand_all_key_types(df: pl.DataFrame, key_types: list[str] | None = None) -> pl.DataFrame:
    prepared = _with_clean_keys(df)
    selected_key_types = key_types or list(VALID_KEY_TYPES)
    frames = []
    for key_type in selected_key_types:
        frame = prepared.with_columns(pl.lit(key_type).alias("key_type"))
        frames.append(_selected_key_frame(frame, key_type))
    if not frames:
        return prepared.clear()
    return pl.concat(frames, how="diagonal_relaxed")


def build_selected_key_snapshot(df: pl.DataFrame) -> pl.DataFrame:
    prepared = _with_clean_keys(df)
    inferred_key_type = (
        pl.when(pl.col("key_type").is_not_null())
        .then(pl.col("key_type"))
        .when(pl.col("PID").is_not_null() & pl.col("ID").is_not_null())
        .then(pl.lit("pid_id"))
        .when(pl.col("ID").is_not_null())
        .then(pl.lit("id"))
        .when(pl.col("PID").is_not_null())
        .then(pl.lit("pid"))
        .otherwise(pl.lit(None, dtype=pl.Utf8))
    )
    selected = prepared.with_columns(inferred_key_type.alias("key_type"))
    frames = [_selected_key_frame(selected, key_type) for key_type in VALID_KEY_TYPES]
    return pl.concat(frames, how="diagonal_relaxed").select(BASE_KEY_COLUMNS)


def build_history_query_snapshot(df: pl.DataFrame, key_types: list[str] | None = None) -> pl.DataFrame:
    base = build_application_base(df)
    return (
        expand_all_key_types(base, key_types=key_types)
        .select(BASE_KEY_COLUMNS)
        .unique()
        .sort("app_dt", "key_type", "key_value", "PID", "ID")
    )


def expand_keys(df: pl.DataFrame) -> pl.DataFrame:
    return expand_all_key_types(df)


def build_application_key_snapshot(df: pl.DataFrame) -> pl.DataFrame:
    return build_history_query_snapshot(df)
