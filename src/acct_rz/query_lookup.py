from __future__ import annotations

import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.features_blacklist import lookup_step1, lookup_step2
from acct_rz.features_org_blacklist import lookup_step3
from acct_rz.features_windows import lookup_step4
from acct_rz.query_snapshot import build_external_query_snapshot


def lookup_all_steps(
    history_df: pl.DataFrame, query_df: pl.DataFrame, step3_format: str = "long"
) -> dict[str, pl.DataFrame]:
    query_snapshot = build_external_query_snapshot(query_df)
    event_fact = build_default_event_key_fact(history_df)
    return {
        "step1": lookup_step1(query_snapshot, event_fact),
        "step2": lookup_step2(query_snapshot, event_fact),
        "step3": lookup_step3(query_snapshot, event_fact, output_format=step3_format),
        "step4": lookup_step4(query_snapshot, event_fact),
    }
