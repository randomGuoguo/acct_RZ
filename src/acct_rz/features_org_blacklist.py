from __future__ import annotations

import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.keys import build_application_key_snapshot
from acct_rz.normalize import build_application_base


def build_org_class_blacklist_features(df: pl.DataFrame) -> pl.DataFrame:
    """构建机构大类黑名单特征。

    参数:
        df: 原始申请明细。

    返回:
        长表结果，粒度为 `app_dt + key_type + key_value + org_class`。

    规则:
        使用 `Org_class_new` 分组，命中判断仍以 `event_dt <= app_dt` 为准。

    示例:
        同一键可能在 `Bank` 命中、但在 `Rate24` 不命中。

    实现说明:
        先为每个申请快照补全全量机构大类，再按大类左连接违约事件。
    """

    apps = build_application_key_snapshot(df)
    org_classes = (
        build_application_base(df)
        .select(pl.col("Org_class_new").cast(pl.Utf8, strict=False).alias("org_class"))
        .drop_nulls()
        .unique()
        .sort("org_class")
    )
    app_org = apps.join(org_classes, how="cross")
    events = build_default_event_key_fact(df).select(
        "key_type",
        "key_value",
        "event_dt",
        pl.col("Org_class_new").cast(pl.Utf8, strict=False).alias("org_class"),
    )
    matched = app_org.join(events, on=["key_type", "key_value", "org_class"], how="left").with_columns(
        pl.when(pl.col("event_dt").is_not_null() & (pl.col("event_dt") <= pl.col("app_dt")))
        .then(pl.col("event_dt"))
        .otherwise(pl.lit(None, dtype=pl.Date))
        .alias("matched_event_dt")
    )
    return (
        matched.group_by("app_dt", "key_type", "key_value", "org_class")
        .agg(
            (pl.col("matched_event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("black_hit_ever_by_org_class"),
            pl.col("matched_event_dt").min().alias("first_default_event_dt_by_org_class"),
        )
        .sort("app_dt", "key_type", "key_value", "org_class")
    )
