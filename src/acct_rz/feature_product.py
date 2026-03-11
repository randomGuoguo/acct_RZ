from __future__ import annotations

import polars as pl

BLACKLIST_WINDOWS = ("3m", "6m", "9m", "12m", "24m", "36m")
STABLE_ORG_TYPES = ("bank", "rate24", "rate36")
STABLE_PERF_TYPES = ("fpd", "dpd")
BASE_FEATURE_KEY_COLUMNS = ("app_dt", "key_type", "key_value", "PID", "ID")


def window_token_to_offset(window: str) -> str:
    return f"-{int(window[:-1])}mo"


def normalize_org_type_expr(source: str = "Org_class_new", alias: str = "org_type") -> pl.Expr:
    return pl.col(source).cast(pl.Utf8, strict=False).str.strip_chars().str.to_lowercase().alias(alias)


def normalize_perf_type_expr(source: str = "perf_type", alias: str = "perf_type") -> pl.Expr:
    return pl.col(source).cast(pl.Utf8, strict=False).str.strip_chars().str.to_lowercase().alias(alias)
