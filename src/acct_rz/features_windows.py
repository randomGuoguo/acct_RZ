from __future__ import annotations

import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.keys import build_application_key_snapshot


def build_window_count_features(df: pl.DataFrame) -> pl.DataFrame:
    """构建滚动窗口违约次数特征。

    参数:
        df: 原始申请明细。

    返回:
        粒度为 `app_dt + key_type + key_value` 的窗口计数特征表。

    规则:
        先要求 `event_dt <= app_dt`，再按 3/6/12 个月窗口统计次数。

    示例:
        近 3 个月统计只纳入 `app_dt - 3mo` 之后且截至 `app_dt` 的事件。

    实现说明:
        统一左连接事件事实后，用布尔条件聚合不同窗口和分组计数。
    """

    apps = build_application_key_snapshot(df)
    events = build_default_event_key_fact(df).select(
        "key_type",
        "key_value",
        "event_dt",
        pl.col("Org_class_new").cast(pl.Utf8, strict=False).alias("org_class"),
        pl.col("perf_type").cast(pl.Utf8, strict=False).alias("perf_type"),
    )
    joined = apps.join(events, on=["key_type", "key_value"], how="left").with_columns(
        pl.when(pl.col("event_dt").is_not_null() & (pl.col("event_dt") <= pl.col("app_dt")))
        .then(pl.col("event_dt"))
        .otherwise(pl.lit(None, dtype=pl.Date))
        .alias("matched_event_dt")
    )
    return (
        joined.group_by("app_dt", "key_type", "key_value")
        .agg(
            ((pl.col("matched_event_dt").is_not_null()) & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))).sum().alias("default_cnt_3m"),
            ((pl.col("matched_event_dt").is_not_null()) & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-6mo"))).sum().alias("default_cnt_6m"),
            ((pl.col("matched_event_dt").is_not_null()) & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-12mo"))).sum().alias("default_cnt_12m"),
            (
                (pl.col("matched_event_dt").is_not_null())
                & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                & (pl.col("org_class") == "Bank")
            ).sum().alias("default_cnt_3m_bank"),
            (
                (pl.col("matched_event_dt").is_not_null())
                & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-6mo"))
                & (pl.col("org_class") == "Bank")
            ).sum().alias("default_cnt_6m_bank"),
            (
                (pl.col("matched_event_dt").is_not_null())
                & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                & (pl.col("org_class") == "Rate24")
            ).sum().alias("default_cnt_3m_rate24"),
            (
                (pl.col("matched_event_dt").is_not_null())
                & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                & (pl.col("perf_type") == "fpd")
            ).sum().alias("default_cnt_3m_fpd"),
            (
                (pl.col("matched_event_dt").is_not_null())
                & (pl.col("matched_event_dt") > pl.col("app_dt").dt.offset_by("-3mo"))
                & (pl.col("perf_type") == "dpd")
            ).sum().alias("default_cnt_3m_dpd"),
        )
        .sort("app_dt", "key_type", "key_value")
    )
