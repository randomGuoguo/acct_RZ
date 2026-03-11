# acct_RZ Architecture 2026-03-11

## 1. 文档目标

本文档面向后续接手项目的人类工程师和智能体，目标是用系统设计文档的方式说明当前项目的真实架构、主产物边界、核心数据流、模块职责、测试覆盖和后续扩展风险。

本文档优先回答以下问题：

- 当前项目的主产品是什么
- `batch` 与 `query` 两条链路如何共用同一套特征逻辑
- `y.csv` 如何被转换为 `blacklist_features.parquet`
- `step1` 到 `step4` 当前还承担什么角色
- 哪些模块是稳定骨架，哪些模块只是兼容层
- 当前测试保护了哪些关键契约

## 2. 项目定位

`acct_RZ` 是一个基于 `Polars` 的违约历史特征构建与查询项目，围绕历史申请样本 `y.csv` 提供两类能力：

- `batch` 模式：从历史样本全量生成模型可消费的宽表特征文件
- `query` 模式：对外部查询快照按指定 `app_dt` 和 `key` 返回同一套特征结果

截至 2026-03-11，项目的主产品边界已经切换为：

- `blacklist_features.parquet`

而不是旧的：

- `step1_blacklist.parquet`
- `step2_traceback.parquet`
- `step3_org_blacklist.parquet`
- `step4_window_counts.parquet`

上述四个 `step` 文件仍然保留，但它们只承担兼容输出角色，不再是产品定义本身。

## 3. 总体架构

### 3.1 架构分层

当前项目可以分成 6 层：

1. 输入与编排层
   - `run_pipeline.py`
   - `src/acct_rz/pipeline.py`
   - `src/acct_rz/query_lookup.py`
2. 标准化与查询协议层
   - `src/acct_rz/normalize.py`
   - `src/acct_rz/keys.py`
   - `src/acct_rz/query_snapshot.py`
   - `src/acct_rz/lookup_base.py`
3. 事实层
   - `src/acct_rz/events.py`
4. 聚合层
   - `src/acct_rz/agg_lifetime.py`
   - `src/acct_rz/agg_windows.py`
   - `src/acct_rz/agg_breakdown.py`
   - `src/acct_rz/agg_recency.py`
5. 标签族与产品装配层
   - `src/acct_rz/labels_history.py`
   - `src/acct_rz/labels_window.py`
   - `src/acct_rz/labels_orgtype.py`
   - `src/acct_rz/labels_perftype.py`
   - `src/acct_rz/labels_complexity.py`
   - `src/acct_rz/product_blacklist_features.py`
6. 兼容层
   - `src/acct_rz/features_blacklist.py`
   - `src/acct_rz/features_org_blacklist.py`
   - `src/acct_rz/features_windows.py`

### 3.2 核心判断

当前系统不是“每个 step 直接读取原始 `y.csv` 并各算各的”。

当前系统的稳定骨架是：

- `query_snapshot`
- `event_fact`

并在此之上构建：

- 复用聚合层
- 复用标签族
- 最终产品装配
- 兼容 step 输出

这意味着未来新增特征时，优先应该增加新的聚合或新的标签族，而不是继续在 `step4` 之类的兼容模块里直接堆字段。

### 3.3 总体流程图

```text
                         +--------------------+
                         |   run_pipeline.py  |
                         +--------------------+
                           |              |
                           | batch        | query
                           v              v
              +------------------+   +-------------------+
              | pipeline.py      |   | query_lookup.py   |
              +------------------+   +-------------------+
                           |              |
                           +------+-------+
                                  |
                                  v
                     +---------------------------+
                     | history_df / query_df     |
                     +---------------------------+
                                  |
                 +----------------+----------------+
                 |                                 |
                 v                                 v
       +----------------------+        +----------------------+
       | query_snapshot       |        | event_fact           |
       | keys.py /            |        | events.py            |
       | query_snapshot.py    |        +----------------------+
       +----------------------+
                 |
                 v
    +------------------------------------------------------+
    | agg_lifetime / agg_windows / agg_breakdown / recency |
    +------------------------------------------------------+
                                  |
                                  v
    +------------------------------------------------------+
    | history / window / orgtype / perftype / complexity   |
    | labels                                                |
    +------------------------------------------------------+
                                  |
                                  v
                 +----------------------------------+
                 | blacklist_features.parquet       |
                 +----------------------------------+
                                  |
                                  v
                 +----------------------------------+
                 | step1~step4 compatibility output |
                 +----------------------------------+
```

## 4. 运行模式

### 4.1 Batch 模式

入口函数：

- `run_demo_pipeline(input_path, out_dir)`

执行顺序：

1. 读取历史样本 `y.csv`
2. 生成历史查询快照 `query_snapshot`
3. 生成共享事件事实表 `event_fact`
4. 组装主宽表 `blacklist_features`
5. 同步输出兼容文件 `step1` 到 `step4`

当前 `batch` 模式的主结果是：

- `blacklist_features.parquet`

### 4.2 Query 模式

入口函数：

- `lookup_all_steps(history_df, query_df, step3_format="long")`

执行顺序：

1. 读取历史样本作为事实源
2. 读取外部 `query.csv`
3. 构建外部查询快照
4. 复用共享事件事实表
5. 返回 `blacklist_features` 以及 `step1` 到 `step4`

当前 `query` 模式的主返回结果已经包含：

- `blacklist_features`

同时仍附带兼容字段集合：

- `step1`
- `step2`
- `step3`
- `step4`

### 4.3 两条链路为何可以共用逻辑

因为下游特征逻辑只依赖两类统一输入：

- `query_snapshot`
- `event_fact`

只要这两个对象结构稳定，`batch` 与 `query` 的特征计算逻辑就可以完全复用。

## 5. 核心数据模型

### 5.1 application_base

来源：

- `src/acct_rz/normalize.py`

职责：

- 解析 `app_dt`
- 清洗 `PID` / `ID`
- 处理 `mob`
- 推导 `is_default`
- 推导 `event_dt`

当前关键规则：

- `target == 1` 视为违约
- `mob` 缺失时按 `6` 处理
- `event_dt = app_dt + mob_filled months`
- `app_dt` 同时兼容 `YYYYMMDD` 与 `YYYY-MM-DD`

### 5.2 query_snapshot

来源：

- `src/acct_rz/query_snapshot.py`
- `src/acct_rz/keys.py`

标准键列：

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

支持的查询视角：

- `pid_id`
- `pid`
- `id`

### 5.3 event_fact

来源：

- `src/acct_rz/events.py`

作用：

- 从历史样本中抽取违约事件
- 按受支持的 `key_type` 展开为共享事件事实表

关键列：

- `event_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`
- `Org_class_new`
- `perf_type`

### 5.4 blacklist_features

来源：

- `src/acct_rz/product_blacklist_features.py`

粒度：

- 每个查询键一行

主键：

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

包含的特征族：

- lifetime history
- rolling windows
- stable org_type breakdown
- stable perf_type breakdown
- complexity features

### 5.5 step compatibility outputs

来源：

- `src/acct_rz/features_blacklist.py`
- `src/acct_rz/features_org_blacklist.py`
- `src/acct_rz/features_windows.py`

当前语义：

- 不再定义产品边界
- 仅用于兼容旧接口、旧测试和旧消费方式

## 6. 模块职责说明

### 6.1 `feature_product.py`

职责：

- 定义基础键列
- 定义窗口配置
- 定义稳定维度枚举
- 提供维度归一化与窗口辅助函数

这是产品约束的公共常量层。

### 6.2 聚合层

`agg_lifetime.py`

- 负责 lifetime 命中、首末次日期、累计次数、月次数

`agg_windows.py`

- 负责 `3m/6m/9m/12m/24m/36m` 多窗口统计

`agg_breakdown.py`

- 负责按维度生成长表 breakdown，目前支持 `org_type` 与 `perf_type`

`agg_recency.py`

- 负责从日期列派生 `days_since_*`

### 6.3 标签族层

`labels_history.py`

- 将 lifetime 聚合变成模型字段

`labels_window.py`

- 将窗口聚合变成模型字段

`labels_orgtype.py`

- 只展开稳定机构类目，不做高基数扩展

`labels_perftype.py`

- 只展开稳定表现类目

`labels_complexity.py`

- 提供 multi-head 和 latest type 结构型特征

### 6.4 产品装配层

`product_blacklist_features.py`

- 将各标签族按主键左连接
- 检查重复列
- 检查 join 前后行数不变
- 输出稳定宽表

### 6.5 兼容层

`features_blacklist.py`

- 将 history family 映射回 `step1` / `step2`

`features_org_blacklist.py`

- 将 breakdown 长表映射回 `step3`

`features_windows.py`

- 从新 family 中取子集映射回 `step4`

## 7. 产品规则与边界

### 7.1 主产品边界

主产品边界明确为：

- `blacklist_features.parquet`

不是：

- `step1~step4`

### 7.2 稳定展开边界

当前宽表只展开稳定低基数维度：

- `org_type`: `bank`, `rate24`, `rate36`
- `perf_type`: `fpd`, `dpd`

### 7.3 V1 非目标

截至 2026-03-11，以下内容不进入主宽表：

- `sample_flag` 展开
- 高基数 channel 级维度展开
- 单机构名称级宽表展开

### 7.4 未命中返回契约

未命中历史时：

- 保留查询行
- count 类字段为 `0` 或空值填充后的稳定输出
- date 类字段为 `null`

## 8. 输入输出契约

### 8.1 输入契约

外部查询输入至少需要：

- `app_dt`
- 合法的 `PID` / `ID` 组合

显式 `key_type` 若存在，必须属于：

- `pid`
- `id`
- `pid_id`

### 8.2 输出契约

主宽表和兼容输出共享基础主键列：

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

最终对外日期列统一序列化为：

- `YYYYMMDD`
- `Int64`

### 8.3 产品级保护

当前装配层已经显式保护：

- 重复列检测
- join 后行数不变
- 稳定列名约定

## 9. 当前测试覆盖

截至 2026-03-11，测试已经覆盖：

- 标准化与日期解析
- key snapshot 协议
- 事件事实表
- lifetime / windows / breakdown / recency 聚合
- history / window / breakdown / complexity 标签族
- `blacklist_features` 产品装配
- `step1` 到 `step4` 兼容行为
- `pipeline.py` 和 `run_pipeline.py` 的主链路
- `README.md` 基本契约提示

最近一次全量结果：

- `33 passed`
- 日期：2026-03-11

## 10. 当前风险与限制

- `step3` 仍只支持 `long` 输出
- 兼容层仍然存在，后续维护时容易被误当成主产品层
- 文档中旧的 `architecture.md` / `TASK2.md` 仍保留历史内容，阅读时需要优先看 2026-03-11 版本
- 高基数 detail 表尚未正式落地
- 业务规则仍主要写在代码里，尚未配置化

## 11. 维护建议

### 11.1 新增特征时的优先顺序

推荐顺序：

1. 判断是否属于已有标签族
2. 若不是，先增加聚合层能力
3. 再增加新的标签族
4. 最后接入产品装配层

不推荐：

- 直接在 `features_windows.py` 之类兼容层里加新逻辑

### 11.2 修改规则时先看哪里

- 改违约规则：先看 `normalize.py`
- 改键协议：先看 `keys.py` / `query_snapshot.py`
- 改公共时间匹配：先看 `lookup_base.py`
- 改产品边界：先看 `feature_product.py` 和 `product_blacklist_features.py`

### 11.3 后续扩展建议

- 增加 `blacklist_feature_detail` 长表产品
- 将 `sample_flag` 放入 detail 层而不是主宽表
- 为配置化维度和窗口建立统一配置入口

## 12. 代码入口索引

- CLI 入口：`run_pipeline.py`
- batch 编排：`src/acct_rz/pipeline.py`
- query 编排：`src/acct_rz/query_lookup.py`
- 标准化：`src/acct_rz/normalize.py`
- 键协议：`src/acct_rz/keys.py`
- query snapshot：`src/acct_rz/query_snapshot.py`
- 事件事实：`src/acct_rz/events.py`
- 聚合层：`src/acct_rz/agg_*.py`
- 标签族：`src/acct_rz/labels_*.py`
- 主产品装配：`src/acct_rz/product_blacklist_features.py`
- 兼容层：`src/acct_rz/features_*.py`
