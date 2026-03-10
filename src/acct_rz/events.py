from __future__ import annotations

import polars as pl

from acct_rz.keys import expand_keys
from acct_rz.normalize import build_application_base


def build_default_event_key_fact(df: pl.DataFrame) -> pl.DataFrame:
    """构建违约事件键事实表。

    参数:
        df: 原始申请明细。

    返回:
        仅包含违约事件的键事实表，保留机构与表现维度。

    规则:
        只保留 `is_default == 1` 的记录；事件时间使用 `event_dt`。

    示例:
        一条违约申请会按 `pid_id`、`pid`、`id` 三个口径展开。

    实现说明:
        违约事件先标准化，再扩成长表键空间供后续统一检索。
    """

    base = build_application_base(df)
    defaults = base.filter(pl.col("is_default") == 1)
    return expand_keys(defaults).sort("event_dt", "key_type", "key_value")
