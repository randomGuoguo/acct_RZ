from __future__ import annotations

import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.keys import build_application_key_snapshot


def _with_matched_event_dt(joined: pl.DataFrame) -> pl.DataFrame:
    return joined.with_columns(
        pl.when(pl.col("event_dt").is_not_null() & (pl.col("event_dt") <= pl.col("app_dt")))
        .then(pl.col("event_dt"))
        .otherwise(pl.lit(None, dtype=pl.Date))
        .alias("matched_event_dt")
    )


def build_blacklist_asof_features(df: pl.DataFrame) -> pl.DataFrame:
    """构建截至申请日的黑名单特征。

    参数:
        df: 原始申请明细。

    返回:
        以 `app_dt + key_type + key_value` 为粒度的截至日特征表。

    规则:
        只有 `event_dt <= app_dt` 的违约事件才记为命中。

    示例:
        `event_dt=2024-09-10` 在 `2024-10-01` 会命中，在 `2024-09-01` 不命中。

    实现说明:
        申请快照与违约事件按统一键空间左连接后聚合。
    """

    apps = build_application_key_snapshot(df)
    events = build_default_event_key_fact(df).select("key_type", "key_value", "event_dt")
    matched = _with_matched_event_dt(apps.join(events, on=["key_type", "key_value"], how="left"))
    return (
        matched.group_by("app_dt", "key_type", "key_value")
        .agg(
            (pl.col("matched_event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("black_hit_ever"),
            pl.col("matched_event_dt").min().alias("first_default_event_dt"),
            pl.col("matched_event_dt").max().alias("latest_default_event_dt"),
            pl.col("matched_event_dt").is_not_null().sum().alias("hit_event_cnt_asof_dt"),
        )
        .sort("app_dt", "key_type", "key_value")
    )


def build_step1_blacklist_product(df: pl.DataFrame) -> pl.DataFrame:
    """构建 step1 黑名单产品。

    参数:
        df: 原始申请明细。

    返回:
        包含是否历史命中及首次命中日期的结果表。

    规则:
        复用统一截至日逻辑，仅保留 step1 所需字段。

    示例:
        命中过的键会返回 `black_hit_ever=1` 与首次命中日。

    实现说明:
        直接从黑名单截至日特征裁剪字段，避免重复维护规则。
    """

    return build_blacklist_asof_features(df).select("app_dt", "key_type", "key_value", "black_hit_ever", "first_default_event_dt")


def build_step2_traceback_product(df: pl.DataFrame) -> pl.DataFrame:
    """构建 step2 可回溯黑名单产品。

    参数:
        df: 原始申请明细。

    返回:
        包含截至日命中状态、累计命中次数和最近命中日的结果表。

    规则:
        仍以 `event_dt <= app_dt` 为判断边界。

    示例:
        同一键在不同申请日可呈现从未命中到已命中的状态变化。

    实现说明:
        step2 与 step1 共用同一套截至日聚合，只是输出列更完整。
    """

    return build_blacklist_asof_features(df)
