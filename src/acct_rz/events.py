from __future__ import annotations

import polars as pl

from acct_rz.keys import expand_all_key_types
from acct_rz.normalize import build_application_base


def build_default_event_key_fact(df: pl.DataFrame, key_types: list[str] | None = None) -> pl.DataFrame:
    base = build_application_base(df)
    defaults = base.filter(pl.col("is_default") == 1)
    return expand_all_key_types(defaults, key_types=key_types).sort("event_dt", "key_type", "key_value", "PID", "ID")
